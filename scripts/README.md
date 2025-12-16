# Scripts de S3-Wire

Este directorio contiene scripts para generar links temporales de upload.

## 📋 Descripción

El script `generate-upload-link.py` automatiza el proceso de creación de links de upload:

1. Genera un ID corto aleatorio (base62)
2. Crea una URL pre-firmada de S3 para permitir uploads
3. Renderiza una página HTML desde el template
4. Sube la página HTML al bucket de hosting
5. Muestra el link completo para compartir

## 🚀 Instalación

### 1. Crear Entorno Virtual (Recomendado)

```bash
cd scripts
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

## 📝 Uso

### Sintaxis Básica

```bash
python generate-upload-link.py \
  --domain DOMAIN \
  --storage-bucket STORAGE_BUCKET \
  --hosting-bucket HOSTING_BUCKET \
  [OPTIONS]
```

### Parámetros Requeridos

- `--domain`: Dominio del bucket de hosting (ej: `up.mydomain.com`)
- `--storage-bucket`: Nombre del bucket de almacenamiento
- `--hosting-bucket`: Nombre del bucket de hosting

### Parámetros Opcionales

- `--ttl`: Tiempo de vida en segundos (default: 86400 = 24 horas)
- `--max-size`: Tamaño máximo en bytes (default: 104857600 = 100 MB)
- `--allowed-types`: Tipos MIME permitidos separados por coma (default: `*/*`)
- `--filename`: Nombre del archivo en S3 (default: auto-generado)
- `--region`: Región de AWS (default: región por defecto de AWS CLI)

## 📚 Ejemplos

### Ejemplo 1: Uso Básico

```bash
python generate-upload-link.py \
  --domain up.mydomain.com \
  --storage-bucket my-storage-bucket \
  --hosting-bucket up.mydomain.com
```

Output:
```
✅ Link generado exitosamente!
🔗 Link de upload: http://up.mydomain.com/u/a3Xk9p/
⏰ Válido hasta: 2024-01-16 14:30:00 UTC
🆔 ID: a3Xk9p
```

### Ejemplo 2: Solo Imágenes, 1 Hora

```bash
python generate-upload-link.py \
  --domain up.mydomain.com \
  --storage-bucket my-storage-bucket \
  --hosting-bucket up.mydomain.com \
  --ttl 3600 \
  --allowed-types "image/*"
```

### Ejemplo 3: PDF hasta 50MB

```bash
python generate-upload-link.py \
  --domain up.mydomain.com \
  --storage-bucket my-storage-bucket \
  --hosting-bucket up.mydomain.com \
  --max-size 52428800 \
  --allowed-types "application/pdf"
```

### Ejemplo 4: Múltiples Tipos

```bash
python generate-upload-link.py \
  --domain up.mydomain.com \
  --storage-bucket my-storage-bucket \
  --hosting-bucket up.mydomain.com \
  --allowed-types "image/*,application/pdf,text/plain"
```

### Ejemplo 5: Nombre de Archivo Específico

```bash
python generate-upload-link.py \
  --domain up.mydomain.com \
  --storage-bucket my-storage-bucket \
  --hosting-bucket up.mydomain.com \
  --filename documento-importante.pdf
```

### Ejemplo 6: Región Específica

```bash
python generate-upload-link.py \
  --domain up.mydomain.com \
  --storage-bucket my-storage-bucket \
  --hosting-bucket up.mydomain.com \
  --region us-west-2
```

## 🔧 Configuración de AWS

### Credenciales

El script usa las credenciales configuradas en AWS CLI. Opciones:

#### Opción 1: AWS CLI Profile

```bash
aws configure
```

Esto configurará:
- AWS Access Key ID
- AWS Secret Access Key
- Default region
- Output format

#### Opción 2: Variables de Entorno

```bash
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1
```

#### Opción 3: IAM Role (EC2/ECS)

Si ejecutas en EC2 o ECS con IAM Role asignado, las credenciales se obtienen automáticamente.

### Permisos Necesarios

El usuario/role de AWS debe tener permisos para:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": [
        "arn:aws:s3:::HOSTING-BUCKET/u/*",
        "arn:aws:s3:::STORAGE-BUCKET/inbox/*"
      ]
    }
  ]
}
```

## 📤 Workflow Completo

### 1. Generar Link

```bash
python generate-upload-link.py \
  --domain up.mydomain.com \
  --storage-bucket my-storage-bucket \
  --hosting-bucket up.mydomain.com
```

### 2. Compartir Link

Envía el link generado al usuario por:
- Email
- Chat (Slack, Teams, etc.)
- SMS
- Cualquier otro medio

### 3. Usuario Sube Archivo

El usuario:
1. Abre el link en su navegador
2. Arrastra o selecciona un archivo
3. El archivo se sube directamente a S3
4. Recibe confirmación de éxito

### 4. Acceder al Archivo

```bash
# Listar archivos
aws s3 ls s3://STORAGE-BUCKET/inbox/

# Descargar archivo
aws s3 cp s3://STORAGE-BUCKET/inbox/FILENAME ./
```

## 🔐 Seguridad

### Buenas Prácticas

1. **No Reutilizar IDs**: Genera un nuevo link para cada upload
2. **TTL Corto**: Usa el TTL mínimo necesario
3. **Tipos Específicos**: Restringe tipos MIME cuando sea posible
4. **Tamaño Limitado**: Ajusta `max-size` según necesidad
5. **Monitoreo**: Revisa regularmente los archivos subidos
6. **Rotación**: No uses el mismo dominio indefinidamente

### Limitaciones

- La URL pre-firmada es válida por el tiempo especificado
- No hay autenticación del usuario
- Cualquiera con el link puede subir un archivo
- El link expira según el TTL configurado

## 🐛 Troubleshooting

### Error: "No se encontraron credenciales de AWS"

**Solución**: Configura credenciales con `aws configure`

### Error: "Access Denied"

**Causa**: Permisos insuficientes

**Solución**: Verifica que el usuario tenga permisos de `s3:PutObject`

### Error: "Template no encontrado"

**Causa**: El archivo `templates/upload-page.html` no existe

**Solución**: Asegúrate de que el template existe en la ruta correcta

### Error al subir HTML a S3

**Causa**: Bucket no existe o no tienes permisos

**Solución**:
1. Verifica que el bucket existe: `aws s3 ls s3://BUCKET-NAME/`
2. Confirma permisos de escritura

## 📊 Monitoreo

### Ver Archivos Subidos

```bash
# Listar todos los archivos
aws s3 ls s3://STORAGE-BUCKET/inbox/ --recursive

# Ver tamaño total
aws s3 ls s3://STORAGE-BUCKET/inbox/ --recursive --summarize
```

### Ver Páginas HTML Generadas

```bash
# Listar páginas
aws s3 ls s3://HOSTING-BUCKET/u/ --recursive

# Ver con fechas
aws s3 ls s3://HOSTING-BUCKET/u/ --recursive --human-readable
```

## 🔄 Automatización

### Script Bash de Ejemplo

```bash
#!/bin/bash
# generate-and-send.sh

EMAIL=$1
LINK=$(python generate-upload-link.py \
  --domain up.mydomain.com \
  --storage-bucket my-storage-bucket \
  --hosting-bucket up.mydomain.com | grep "Link de upload" | cut -d' ' -f4)

echo "Tu link de upload: $LINK" | mail -s "Link de Upload" $EMAIL
```

Uso:
```bash
./generate-and-send.sh user@example.com
```

## 📚 Dependencias

- **boto3**: AWS SDK para Python
- **botocore**: Core de boto3

Ver `requirements.txt` para versiones específicas.

## 🧪 Testing

### Test Manual

```bash
# Generar link
python generate-upload-link.py \
  --domain DOMAIN \
  --storage-bucket BUCKET \
  --hosting-bucket BUCKET

# Abrir link en navegador
# Subir archivo de prueba
# Verificar en S3
aws s3 ls s3://BUCKET/inbox/
```

## 📝 Notas

- Los IDs cortos usan base62 (a-zA-Z0-9) para URLs amigables
- Las páginas HTML se eliminan automáticamente después de 7 días
- Los archivos en `inbox/` permanecen indefinidamente (o según lifecycle rules)
- El script es idempotente: puedes ejecutarlo múltiples veces

## 🤝 Contribuciones

Para añadir funcionalidades o reportar bugs, abre un issue en GitHub.

---

**¿Preguntas?** Consulta el README principal del proyecto.