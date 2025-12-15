import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as route53 from 'aws-cdk-lib/aws-route53';

export interface S3WireStackProps extends cdk.StackProps {
  domain?: string;
  hostedZoneId?: string;
  hostedZoneName?: string;
}

export class S3WireStack extends cdk.Stack {
  public readonly storageBucket: s3.Bucket;
  public readonly hostingBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props?: S3WireStackProps) {
    super(scope, id, props);

    // ========================================
    // Bucket de Almacenamiento
    // ========================================
    // Este bucket almacena los archivos subidos por los usuarios en el prefijo inbox/
    this.storageBucket = new s3.Bucket(this, 'StorageBucket', {
      // Eliminar el bucket cuando se destruya el stack (útil para desarrollo)
      // En producción, cambiar a RETAIN
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      
      // Versioning deshabilitado según requerimientos
      versioned: false,
      
      // Encriptación habilitada
      encryption: s3.BucketEncryption.S3_MANAGED,
      
      // Bloquear todo acceso público
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      
      // CORS configuración para permitir uploads desde el sitio web
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.PUT,
            s3.HttpMethods.POST,
          ],
          allowedOrigins: ['*'], // En producción, especificar dominios permitidos
          allowedHeaders: ['*'],
          maxAge: 3000,
        },
      ],
      
      // Reglas de lifecycle
      lifecycleRules: [
        {
          // Opcional: transición de archivos en inbox/ a Glacier después de 30 días
          id: 'TransitionToGlacier',
          prefix: 'inbox/',
          transitions: [
            {
              storageClass: s3.StorageClass.GLACIER,
              transitionAfter: cdk.Duration.days(30),
            },
          ],
          enabled: true,
        },
      ],
    });

    // ========================================
    // Bucket de Hosting Estático
    // ========================================
    // Este bucket sirve las páginas HTML efímeras en el prefijo u/
    const hostingBucketName = props?.domain || undefined;
    
    this.hostingBucket = new s3.Bucket(this, 'HostingBucket', {
      bucketName: hostingBucketName,
      
      // Eliminar el bucket cuando se destruya el stack
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      
      // Versioning deshabilitado
      versioned: false,
      
      // Configuración de Static Website Hosting
      websiteIndexDocument: 'index.html',
      websiteErrorDocument: '404.html',
      
      // Permitir acceso público para lectura de objetos específicos
      publicReadAccess: false, // Lo configuraremos con política más específica
      blockPublicAccess: new s3.BlockPublicAccess({
        blockPublicAcls: false,
        blockPublicPolicy: false,
        ignorePublicAcls: false,
        restrictPublicBuckets: false,
      }),
      
      // CORS para permitir acceso desde cualquier origen
      cors: [
        {
          allowedMethods: [
            s3.HttpMethods.GET,
            s3.HttpMethods.HEAD,
          ],
          allowedOrigins: ['*'],
          allowedHeaders: ['*'],
          maxAge: 3000,
        },
      ],
      
      // Reglas de lifecycle para eliminar páginas HTML efímeras
      lifecycleRules: [
        {
          // Eliminar automáticamente objetos en u/ después de 7 días
          id: 'DeleteEphemeralPages',
          prefix: 'u/',
          expiration: cdk.Duration.days(7),
          enabled: true,
        },
      ],
    });

    // ========================================
    // Políticas de Bucket
    // ========================================
    
    // Política para el bucket de hosting: permitir GetObject público solo en u/
    this.hostingBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        sid: 'PublicReadGetObject',
        effect: iam.Effect.ALLOW,
        principals: [new iam.AnyPrincipal()],
        actions: ['s3:GetObject'],
        resources: [
          this.hostingBucket.arnForObjects('u/*'),
          this.hostingBucket.arnForObjects('index.html'),
          this.hostingBucket.arnForObjects('404.html'),
        ],
      })
    );

    // Política para el bucket de almacenamiento: solo PutObject con URLs pre-firmadas
    // Las URLs pre-firmadas ya incluyen los permisos necesarios mediante IAM del usuario
    // que genera las URLs, por lo que no necesitamos política adicional aquí
    
    // Sin embargo, podemos añadir una política que deniegue PutObject sin pre-firma
    // Nota: Las URLs pre-firmadas usan las credenciales del firmante, no del bucket
    
    // ========================================
    // Route53 (Opcional)
    // ========================================
    if (props?.hostedZoneId && props?.hostedZoneName && props?.domain) {
      // Importar la Hosted Zone existente
      const hostedZone = route53.HostedZone.fromHostedZoneAttributes(
        this,
        'HostedZone',
        {
          hostedZoneId: props.hostedZoneId,
          zoneName: props.hostedZoneName,
        }
      );

      // Crear registro A Alias apuntando al S3 Website Endpoint
      new route53.ARecord(this, 'WebsiteAliasRecord', {
        zone: hostedZone,
        recordName: props.domain,
        target: route53.RecordTarget.fromAlias({
          bind: () => ({
            dnsName: this.hostingBucket.bucketWebsiteDomainName,
            hostedZoneId: this.hostingBucket.bucketWebsiteHostedZoneId || '',
          }),
        }),
      });
    }

    // ========================================
    // Outputs
    // ========================================
    new cdk.CfnOutput(this, 'StorageBucketName', {
      value: this.storageBucket.bucketName,
      description: 'Nombre del bucket de almacenamiento para archivos',
      exportName: 'S3Wire-StorageBucketName',
    });

    new cdk.CfnOutput(this, 'HostingBucketName', {
      value: this.hostingBucket.bucketName,
      description: 'Nombre del bucket de hosting para páginas HTML',
      exportName: 'S3Wire-HostingBucketName',
    });

    new cdk.CfnOutput(this, 'WebsiteURL', {
      value: this.hostingBucket.bucketWebsiteUrl,
      description: 'URL del sitio web estático',
      exportName: 'S3Wire-WebsiteURL',
    });

    new cdk.CfnOutput(this, 'HostingBucketDomain', {
      value: this.hostingBucket.bucketWebsiteDomainName,
      description: 'Dominio del bucket de hosting (para configurar DNS)',
      exportName: 'S3Wire-HostingBucketDomain',
    });

    new cdk.CfnOutput(this, 'HostingBucketRegionalDomain', {
      value: this.hostingBucket.bucketRegionalDomainName,
      description: 'Dominio regional del bucket de hosting',
      exportName: 'S3Wire-HostingBucketRegionalDomain',
    });
  }
}
