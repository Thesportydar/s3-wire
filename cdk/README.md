# S3-Wire CDK Infrastructure

Este directorio contiene la definición de infraestructura como código (IaC) usando AWS CDK para el sistema S3-Wire.

## 📋 Descripción

La infraestructura despliega:

- **Bucket de Almacenamiento**: Para archivos subidos (`inbox/` prefix)
- **Bucket de Hosting Estático**: Para páginas HTML efímeras (`u/` prefix)
- **CloudFront Distribution (Opcional)**: CDN con HTTPS cuando se especifica un dominio
- **Certificado ACM (Opcional)**: SSL/TLS para el dominio personalizado
- **Políticas de Acceso**: Configuración de permisos y CORS
- **Lifecycle Rules**: Eliminación automática de páginas HTML después de 7 días
- **Route53 (Opcional)**: Registro DNS A Alias apuntando a CloudFront

## 🚀 Requisitos Previos

- Node.js >= 14.x
- AWS CLI configurado con credenciales válidas
- AWS CDK instalado globalmente:
  ```bash
  npm install -g aws-cdk
  ```

## 📦 Instalación

```bash
# Instalar dependencias
npm install
```

## 🏗️ Despliegue

### 1. Bootstrap de CDK (solo primera vez)

Si nunca has usado CDK en tu cuenta/región:

```bash
cdk bootstrap aws://ACCOUNT-ID/REGION
```

Ejemplo:
```bash
cdk bootstrap aws://123456789012/us-east-1
```

### 2. Síntesis del Stack

Genera el template de CloudFormation:

```bash
npm run build
cdk synth
```

### 3. Despliegue Básico

Sin dominio personalizado:

```bash
cdk deploy
```

### 4. Despliegue con Dominio Personalizado y CloudFront (HTTPS)

#### Opción A: Usar certificado ACM existente (recomendado para producción)

```bash
cdk deploy \
  -c domain=up.mydomain.com \
  -c storageBucketName=my-storage-bucket \
  -c hostedZoneId=Z1234567890ABC \
  -c hostedZoneName=mydomain.com \
  -c certificateArn=arn:aws:acm:us-east-1:123456789012:certificate/abc-123
```

**IMPORTANTE:** El certificado ACM para CloudFront **DEBE estar en us-east-1**, independientemente de la región del stack.

#### Opción B: Crear nuevo certificado automáticamente

```bash
cdk deploy \
  -c domain=up.mydomain.com \
  -c storageBucketName=my-storage-bucket \
  -c hostedZoneId=Z1234567890ABC \
  -c hostedZoneName=mydomain.com
```

El stack creará un certificado ACM nuevo con validación DNS automática.

**⚠️ NOTA IMPORTANTE sobre Regiones:**
- Los certificados ACM para CloudFront **DEBEN estar en us-east-1**
- Si su stack está en **us-east-1**, el certificado se creará automáticamente
- Si su stack está en **otra región**, debe proporcionar un `certificateArn` de un certificado existente en us-east-1
- Para crear un certificado manualmente en us-east-1, use la consola de ACM o AWS CLI

#### Parámetros:
- `domain`: Subdominio completo para el hosting bucket (ej: `up.mydomain.com`)
- `storageBucketName` (opcional): Nombre personalizado para el bucket de almacenamiento (ej: `my-storage-bucket`). Si no se especifica, CDK genera un nombre automático.
- `hostedZoneId`: ID de la Hosted Zone en Route53
- `hostedZoneName`: Nombre de la zona DNS (ej: `mydomain.com`)
- `certificateArn` (opcional): ARN de certificado ACM existente en us-east-1

### 5. Ver Diferencias antes de Desplegar

```bash
cdk diff
```

## 📤 Outputs del Despliegue

Después del despliegue, CDK mostrará:

### Sin CloudFront (despliegue básico):
- **StorageBucketName**: Nombre del bucket de almacenamiento
- **HostingBucketName**: Nombre del bucket de hosting
- **WebsiteURL**: URL del sitio web estático de S3 (HTTP)
- **HostingBucketDomain**: Dominio del bucket para configurar DNS
- **HostingBucketRegionalDomain**: Dominio regional del bucket

### Con CloudFront (dominio personalizado con HTTPS):
- **StorageBucketName**: Nombre del bucket de almacenamiento
- **HostingBucketName**: Nombre del bucket de hosting
- **CloudFrontDistributionId**: ID de la distribución CloudFront (ej: E1234ABCD5678)
- **CloudFrontDomainName**: Dominio CloudFront (ej: d111111abcdef8.cloudfront.net)
- **WebsiteURL**: URL del sitio web con HTTPS (ej: https://up.mydomain.com)
- **HostingBucketDomain**: Dominio del bucket (referencia)
- **HostingBucketRegionalDomain**: Dominio regional del bucket (referencia)

Guarda estos valores para usarlos con el script de generación de links.

## 🔧 Comandos Útiles

```bash
# Compilar TypeScript
npm run build

# Compilar en modo watch
npm run watch

# Ver el template de CloudFormation generado
cdk synth

# Comparar cambios con el stack desplegado
cdk diff

# Desplegar el stack
cdk deploy

# Destruir el stack (¡CUIDADO! Eliminará todos los recursos)
cdk destroy

# Listar todos los stacks
cdk list
```

## 🏗️ Estructura de Archivos

```
cdk/
├── bin/
│   └── s3-wire-app.ts       # Entry point de la aplicación CDK
├── lib/
│   └── s3-wire-stack.ts     # Definición del stack principal
├── package.json             # Dependencias y scripts
├── tsconfig.json            # Configuración de TypeScript
├── cdk.json                 # Configuración de CDK
└── README.md                # Este archivo
```

## 🔐 Recursos Creados

### Bucket de Almacenamiento

- **Propósito**: Almacenar archivos subidos por usuarios
- **Prefijo**: `inbox/`
- **Encriptación**: S3-Managed (SSE-S3)
- **Acceso Público**: Bloqueado
- **CORS**: Configurado para PUT/POST desde cualquier origen
- **Lifecycle**: Transición a Glacier después de 30 días

### Bucket de Hosting

- **Propósito**: Servir páginas HTML efímeras
- **Prefijo**: `u/` para páginas de upload
- **Static Website**: Habilitado
- **Index Document**: `index.html`
- **Error Document**: `404.html`
- **Acceso Público**: Solo GetObject en `u/*`, `index.html`, `404.html`
- **CORS**: Configurado para GET/HEAD desde cualquier origen
- **Lifecycle**: Eliminar objetos en `u/` después de 7 días

### CloudFront Distribution (cuando se especifica dominio)

- **Propósito**: CDN con HTTPS para servir el sitio web
- **Origin**: S3 Website Endpoint del bucket de hosting
- **Origin Protocol**: HTTP_ONLY (S3 Website solo soporta HTTP)
- **Viewer Protocol Policy**: REDIRECT_TO_HTTPS (fuerza HTTPS)
- **Compression**: Habilitada
- **Security Policy**: TLS_V1_2_2021
- **SSL Method**: SNI
- **Error Handling**: 404 → /404.html
- **Certificado**: ACM (existente o creado automáticamente)

### Certificado ACM (cuando se crea automáticamente)

- **Región**: us-east-1 (requerido por CloudFront)
- **Validación**: DNS automática via Route53
- **Dominio**: El especificado en el parámetro `domain`

### Route53 A Record (cuando se proporciona dominio y hosted zone)

- **Tipo**: A Alias
- **Target**: CloudFront Distribution (o S3 Website si no hay CloudFront)
- **Dominio**: El especificado en el parámetro `domain`

## 🔒 Seguridad

### Consideraciones Implementadas

1. **Encriptación en Reposo**: Bucket de almacenamiento encriptado
2. **Acceso Público Limitado**: Solo objetos específicos del hosting son públicos
3. **CORS Restrictivo**: Solo métodos necesarios permitidos
4. **Lifecycle Automático**: Páginas HTML se eliminan automáticamente
5. **Políticas de Bucket**: Permisos mínimos necesarios
6. **HTTPS End-to-End**: CloudFront con certificado SSL/TLS (cuando se usa dominio)
7. **Protección MITM**: Todo el tráfico cifrado previene intercepción de URLs pre-firmadas

### 🔒 Mejora de seguridad: HTTPS con CloudFront

Cuando se despliega con un dominio personalizado, CloudFront proporciona HTTPS:
- ✅ **Previene ataques MITM**: El HTML se sirve cifrado por HTTPS
- ✅ **Protege las URLs pre-firmadas**: Durante la carga de la página inicial
- ✅ **Mejora performance**: CDN edge locations más cercanas al usuario
- ✅ **Incluido en AWS Free Tier**: 1TB/mes transferencia, 10M requests
- ✅ **TLS 1.2+**: Protocolo de seguridad moderno

**Nota**: Sin CloudFront, S3 Static Website Hosting solo soporta HTTP, lo que permite que un atacante MITM intercepte la página HTML y capture las URLs pre-firmadas expuestas en el código JavaScript.

### Mejoras Recomendadas para Producción

1. **CORS Específico**: Cambiar `allowedOrigins: ['*']` por dominios específicos
2. **Logging**: Habilitar S3 Access Logs
3. **Versioning**: Considerar habilitar en bucket de almacenamiento
4. **MFA Delete**: Habilitar para protección adicional
5. **Bucket Policies**: Añadir restricciones adicionales según necesidades
6. **CloudWatch Alarms**: Monitoreo de uso y costos
7. **Removal Policy**: Cambiar a `RETAIN` en producción

## 🧹 Limpieza

Para eliminar todos los recursos creados:

```bash
cdk destroy
```

**ADVERTENCIA**: Esto eliminará:
- Ambos buckets S3 y todo su contenido
- Registros de Route53 (si fueron creados)
- Todos los archivos subidos

Asegúrate de respaldar cualquier dato importante antes de ejecutar este comando.

## 📝 Personalización

### Cambiar Retention de Lifecycle

Edita `lib/s3-wire-stack.ts` y modifica:

```typescript
// Para páginas HTML (actualmente 7 días)
expiration: cdk.Duration.days(7),

// Para archivos en inbox (actualmente 30 días a Glacier)
transitionAfter: cdk.Duration.days(30),
```

### Cambiar Removal Policy

Para producción, cambia:

```typescript
removalPolicy: cdk.RemovalPolicy.RETAIN,
autoDeleteObjects: false,
```

### Añadir CloudWatch Alarms

```typescript
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';

// Alarma para tamaño del bucket
new cloudwatch.Alarm(this, 'BucketSizeAlarm', {
  metric: this.storageBucket.metricBucketSizeBytes(),
  threshold: 100 * 1024 * 1024 * 1024, // 100 GB
  evaluationPeriods: 1,
});
```

## 🐛 Troubleshooting

### Error: "Unable to resolve AWS account"

**Solución**: Configura credenciales AWS:
```bash
aws configure
```

### Error: "Stack already exists"

**Solución**: El stack ya está desplegado. Usa `cdk diff` para ver cambios o `cdk deploy` para actualizar.

### Error: Bucket name already exists

**Solución**: Los nombres de buckets S3 son globalmente únicos. Cambia el parámetro `domain` o deja que CDK genere un nombre automático.

### Error: No bootstrap stack

**Solución**: Ejecuta el bootstrap de CDK:
```bash
cdk bootstrap
```

## 📚 Referencias

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/latest/guide/home.html)
- [AWS CDK API Reference](https://docs.aws.amazon.com/cdk/api/latest/)
- [CDK S3 Construct](https://docs.aws.amazon.com/cdk/api/latest/docs/aws-s3-readme.html)
- [CDK Route53 Construct](https://docs.aws.amazon.com/cdk/api/latest/docs/aws-route53-readme.html)

## 💡 Tips

- Usa `cdk diff` antes de cada despliegue para revisar cambios
- Los nombres de recursos generados automáticamente incluyen el stack name
- Puedes tener múltiples stacks desplegados cambiando el nombre del stack
- Para desarrollo, usa `cdk watch` para auto-desplegar en cambios

---

**Mantenido por el equipo de S3-Wire**