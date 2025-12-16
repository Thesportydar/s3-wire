# S3-Wire 🚀

Sistema serverless para compartir archivos mediante links cortos y temporales usando Amazon S3.

## 📋 Descripción General

S3-Wire permite a usuarios externos subir archivos a Amazon S3 mediante URLs cortas y temporales, sin necesidad de autenticación ni servicios backend activos. Utiliza URLs pre-firmadas de S3 y páginas HTML efímeras hospedadas en S3 Static Website Hosting.

## 🏗️ Arquitectura del Sistema

```
┌─────────────┐
│   Usuario   │
└──────┬──────┘
       │
       │ 1. Accede al link corto
       ▼
┌──────────────────────────┐
│  S3 Static Website       │
│  (up.mydomain.com)       │
│  /u/{short-id}/index.html│
└──────┬───────────────────┘
       │
       │ 2. Upload directo con URL pre-firmada
       ▼
┌──────────────────────────┐
│  S3 Storage Bucket       │
│  inbox/{filename}        │
└──────────────────────────┘

Gestión de Links:
┌──────────────────────────┐
│  Script Python           │
│  - Genera ID corto       │
│  - Crea URL pre-firmada  │
│  - Sube página HTML      │
└──────────────────────────┘
```

### Componentes:

1. **Bucket de Almacenamiento**: Almacena los archivos subidos en `inbox/`
2. **Bucket de Hosting Estático**: Sirve las páginas HTML efímeras en `u/{short-id}/`
3. **URLs Pre-firmadas**: Permiten upload directo a S3 con permisos temporales
4. **Lifecycle Rules**: Eliminan automáticamente las páginas HTML después de 7 días
5. **Script Python**: Genera los links y páginas HTML personalizadas

## 📦 Requisitos Previos

- **Node.js** >= 14.x (para AWS CDK)
- **Python** >= 3.8
- **AWS CLI** configurado con credenciales
- **AWS CDK** instalado globalmente: `npm install -g aws-cdk`
- Cuenta de AWS con permisos para crear recursos S3, IAM y opcionalmente Route53

## 🚀 Instalación

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Thesportydar/s3-wire.git
cd s3-wire
```

### 2. Configurar AWS CDK

```bash
cd cdk
npm install
```

### 3. Configurar Python

```bash
cd scripts
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 🏗️ Despliegue de Infraestructura

### 1. Configurar Parámetros CDK

Edita `cdk/cdk.json` o pasa parámetros por contexto:

```bash
cd cdk

# Opción 1: Despliegue básico
cdk deploy

# Opción 2: Con dominio personalizado
cdk deploy -c domain=up.mydomain.com -c hostedZoneId=Z1234567890ABC
```

### 2. Bootstrap de CDK (primera vez)

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

### 3. Desplegar el Stack

```bash
cdk deploy
```

El despliegue creará:
- Bucket de almacenamiento
- Bucket de hosting estático
- Políticas de bucket
- Reglas de lifecycle
- (Opcional) Registro Route53

### 4. Outputs del Despliegue

Después del despliegue, CDK mostrará:
- `StorageBucketName`: Nombre del bucket de almacenamiento
- `HostingBucketName`: Nombre del bucket de hosting
- `WebsiteURL`: URL del sitio web estático
- `HostingBucketDomain`: Dominio del bucket para configuración

## 📝 Uso del Sistema

### Generar un Link de Upload

```bash
cd scripts
source venv/bin/activate  # Si no está activado

python generate-upload-link.py \
  --domain up.mydomain.com \
  --storage-bucket my-storage-bucket \
  --hosting-bucket up.mydomain.com \
  --ttl 86400 \
  --max-size 104857600 \
  --allowed-types "image/*,application/pdf"
```

#### Parámetros:

- `--domain`: Dominio del bucket de hosting (ej: up.mydomain.com)
- `--storage-bucket`: Nombre del bucket de almacenamiento
- `--hosting-bucket`: Nombre del bucket de hosting
- `--ttl`: Tiempo de vida de la URL en segundos (default: 86400 = 24h)
- `--max-size`: Tamaño máximo de archivo en bytes (default: 100MB)
- `--allowed-types`: Tipos MIME permitidos separados por coma

#### Ejemplo de Output:

```
✓ Link generado exitosamente!

Link de upload: http://up.mydomain.com/u/a3Xk9p/
Válido hasta: 2024-01-16 14:30:00 UTC
ID: a3Xk9p

Compartir este link con el usuario para que suba su archivo.
```

### Compartir el Link

1. Copia el link generado
2. Compártelo con el usuario (email, chat, etc.)
3. El usuario podrá subir un archivo arrastrándolo o seleccionándolo
4. El archivo se guardará en `inbox/{filename}` del bucket de almacenamiento

### Acceder a los Archivos Subidos

Los archivos se guardan en:
```
s3://STORAGE-BUCKET/inbox/nombre-del-archivo.ext
```

Puedes listarlos y descargarlos con AWS CLI:

```bash
# Listar archivos
aws s3 ls s3://STORAGE-BUCKET/inbox/

# Descargar un archivo
aws s3 cp s3://STORAGE-BUCKET/inbox/archivo.pdf ./
```

## 🔐 Consideraciones de Seguridad

### Implementadas:

1. **URLs Pre-firmadas**: Scope limitado a operación PUT únicamente
2. **Expiración Temporal**: Todas las URLs expiran (TTL configurable)
3. **Sin Credenciales Expuestas**: Ningún código contiene credenciales hardcoded
4. **CORS Configurado**: Solo orígenes permitidos pueden hacer uploads
5. **Validación de Tamaño**: Límite de tamaño máximo configurado
6. **Prefijos Aislados**: Contenido separado en `inbox/` y `u/`
7. **Lifecycle Automático**: Las páginas HTML se eliminan después de 7 días
8. **Encriptación**: El bucket de almacenamiento usa encriptación en reposo

### Recomendaciones Adicionales:

- **Monitoreo**: Configura CloudWatch Alarms para detectar uso anormal
- **Logging**: Habilita S3 Access Logs para auditoría
- **Bucket Policies**: Revisa regularmente las políticas de acceso
- **Rotación de Links**: No reutilices IDs cortos
- **Validación de Contenido**: Considera escaneo de malware para archivos subidos
- **Rate Limiting**: Implementa límites con AWS WAF si es necesario

## 🛠️ Troubleshooting

### Error: "Access Denied" al subir archivo

**Causa**: URL pre-firmada expirada o bucket no configurado correctamente

**Solución**:
1. Verifica que el TTL no haya expirado
2. Confirma que las políticas del bucket permiten PutObject
3. Verifica la configuración de CORS

### Error: "File too large"

**Causa**: El archivo excede el tamaño máximo configurado

**Solución**:
- Genera un nuevo link con `--max-size` mayor
- O pide al usuario que reduzca el tamaño del archivo

### La página HTML no carga

**Causa**: El bucket de hosting no está configurado correctamente

**Solución**:
1. Verifica que Static Website Hosting esté habilitado
2. Confirma que la política de bucket permite GetObject público para `u/*`
3. Revisa los logs de S3

### CDK Deploy falla

**Causa**: Permisos insuficientes o configuración incorrecta

**Solución**:
1. Verifica credenciales AWS: `aws sts get-caller-identity`
2. Confirma permisos para crear recursos S3, IAM
3. Revisa los logs de CloudFormation en la consola AWS

### Script Python no encuentra boto3

**Causa**: Dependencias no instaladas

**Solución**:
```bash
cd scripts
pip install -r requirements.txt
```

## 📚 Estructura del Proyecto

```
s3-wire/
├── cdk/                          # Infraestructura AWS CDK
│   ├── bin/
│   │   └── s3-wire-app.ts       # Entry point de CDK
│   ├── lib/
│   │   └── s3-wire-stack.ts     # Definición del stack
│   ├── package.json
│   ├── tsconfig.json
│   ├── cdk.json
│   └── README.md
├── scripts/                      # Scripts de generación
│   ├── generate-upload-link.py  # Generador de links
│   ├── requirements.txt
│   └── README.md
├── templates/                    # Templates HTML
│   └── upload-page.html         # Página de upload
├── .gitignore
└── README.md                     # Este archivo
```

## 🧪 Testing

### Probar el Sistema Completo

1. Despliega la infraestructura con CDK
2. Genera un link de prueba:
   ```bash
   python scripts/generate-upload-link.py \
     --domain HOSTING-BUCKET-NAME \
     --storage-bucket STORAGE-BUCKET-NAME \
     --hosting-bucket HOSTING-BUCKET-NAME
   ```
3. Abre el link en un navegador
4. Sube un archivo de prueba
5. Verifica que aparezca en el bucket de almacenamiento:
   ```bash
   aws s3 ls s3://STORAGE-BUCKET/inbox/
   ```

## 🤝 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una branch para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la branch (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- AWS CDK Team por la excelente documentación
- Comunidad de Python y boto3
- Todos los contribuidores del proyecto

## 📞 Soporte

Para reportar bugs o solicitar features, por favor abre un issue en GitHub.

---

**Hecho con ❤️ para compartir archivos de forma simple y segura**