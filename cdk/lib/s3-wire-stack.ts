import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as targets from 'aws-cdk-lib/aws-route53-targets';

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
    const storageBucketName = this.node.tryGetContext('storageBucketName');
    
    this.storageBucket = new s3.Bucket(this, 'StorageBucket', {
      bucketName: storageBucketName,
      
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
          // Eliminar archivos en inbox/ después de 7 días
          id: 'expire-inbox',
          prefix: 'inbox/',
          expiration: cdk.Duration.days(7),
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(1),
          enabled: true,
        },
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
          enabled: false,  // Deshabilitado porque ya expiramos a los 7 días
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
          // Eliminar automáticamente objetos en u/ después de 1 día
          id: 'expire-upload-pages',
          prefix: 'u/',
          expiration: cdk.Duration.days(1),
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(1),
          enabled: true,
        },
        {
          // Eliminar automáticamente objetos en s/ después de 2 días
          id: 'expire-download-pages',
          prefix: 's/',
          expiration: cdk.Duration.days(2),
          abortIncompleteMultipartUploadAfter: cdk.Duration.days(1),
          enabled: true,
        },
      ],
    });

    // ========================================
    // Políticas de Bucket
    // ========================================
    
    // Política para el bucket de hosting: permitir GetObject público solo en u/ y s/
    this.hostingBucket.addToResourcePolicy(
      new iam.PolicyStatement({
        sid: 'PublicReadGetObject',
        effect: iam.Effect.ALLOW,
        principals: [new iam.AnyPrincipal()],
        actions: ['s3:GetObject'],
        resources: [
          this.hostingBucket.arnForObjects('u/*'),
          this.hostingBucket.arnForObjects('s/*'),
          this.hostingBucket.arnForObjects('index.html'),
        ],
      })
    );

    // Política para el bucket de almacenamiento: solo PutObject con URLs pre-firmadas
    // Las URLs pre-firmadas ya incluyen los permisos necesarios mediante IAM del usuario
    // que genera las URLs, por lo que no necesitamos política adicional aquí
    
    // Sin embargo, podemos añadir una política que deniegue PutObject sin pre-firma
    // Nota: Las URLs pre-firmadas usan las credenciales del firmante, no del bucket
    
    // ========================================
    // CloudFront Distribution
    // ========================================
    
    let distribution: cloudfront.Distribution | undefined;
    
    if (props?.domain) {
      // Obtener parámetro opcional: ARN de certificado ACM existente
      const certificateArn = this.node.tryGetContext('certificateArn');
      
      let certificate: acm.ICertificate;
      
      if (certificateArn) {
        // Usar certificado existente (ej: wildcard *.inaquipaladino.com)
        certificate = acm.Certificate.fromCertificateArn(
          this,
          'ExistingCertificate',
          certificateArn
        );
      } else {
        // Crear nuevo certificado con validación DNS
        // IMPORTANTE: El certificado ACM para CloudFront DEBE estar en us-east-1
        // CDK automatically handles cross-region certificate references for CloudFront
        if (props.hostedZoneId && props.hostedZoneName) {
          const hostedZone = route53.HostedZone.fromHostedZoneAttributes(
            this,
            'HostedZone',
            {
              hostedZoneId: props.hostedZoneId,
              zoneName: props.hostedZoneName,
            }
          );
          
          // DnsValidatedCertificate is deprecated but required for cross-region certificates
          // For us-east-1 stacks, the regular Certificate construct works fine
          // For other regions, users should provide a certificateArn from us-east-1
          certificate = new acm.Certificate(this, 'Certificate', {
            domainName: props.domain,
            validation: acm.CertificateValidation.fromDns(hostedZone),
          });
        } else {
          throw new Error(
            'To automatically create a certificate, both hostedZoneId and hostedZoneName are required. ' +
            'Alternatively, provide an existing certificateArn in us-east-1.'
          );
        }
      }
      
      // Crear CloudFront Distribution
      // Configurar origin usando HttpOrigin para S3 Website Endpoint
      const s3Origin = new origins.HttpOrigin(
        this.hostingBucket.bucketWebsiteDomainName,
        {
          protocolPolicy: cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        }
      );
      
      distribution = new cloudfront.Distribution(this, 'Distribution', {
        defaultBehavior: {
          origin: s3Origin,
          viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
          cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
          compress: true,
        },
        certificate: certificate,
        domainNames: [props.domain],
        errorResponses: [
          {
            httpStatus: 403,
            responseHttpStatus: 200,
            responsePagePath: '/index.html',
            ttl: cdk.Duration.seconds(300),
          },
          {
            httpStatus: 404,
            responseHttpStatus: 200,
            responsePagePath: '/index.html',
            ttl: cdk.Duration.seconds(300),
          },
        ],
        comment: `S3-Wire CloudFront distribution for ${props.domain}`,
      });
      
      // ========================================
      // Route53 (Opcional)
      // ========================================
      if (props.hostedZoneId && props.hostedZoneName) {
        // Importar la Hosted Zone existente
        const hostedZone = route53.HostedZone.fromHostedZoneAttributes(
          this,
          'HostedZoneForRecord',
          {
            hostedZoneId: props.hostedZoneId,
            zoneName: props.hostedZoneName,
          }
        );

        // Crear registro A Alias apuntando a CloudFront
        new route53.ARecord(this, 'AliasRecord', {
          zone: hostedZone,
          recordName: props.domain,
          target: route53.RecordTarget.fromAlias(
            new targets.CloudFrontTarget(distribution)
          ),
        });
      }
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

    if (distribution && props?.domain) {
      // Outputs para CloudFront
      new cdk.CfnOutput(this, 'CloudFrontDistributionId', {
        value: distribution.distributionId,
        description: 'CloudFront Distribution ID',
      });

      new cdk.CfnOutput(this, 'CloudFrontDomainName', {
        value: distribution.distributionDomainName,
        description: 'CloudFront Domain Name',
      });

      new cdk.CfnOutput(this, 'WebsiteURL', {
        value: `https://${props.domain}`,
        description: 'Website URL with HTTPS',
        exportName: 'S3Wire-WebsiteURL',
      });
    } else {
      // Outputs para S3 Website (sin CloudFront)
      new cdk.CfnOutput(this, 'WebsiteURL', {
        value: this.hostingBucket.bucketWebsiteUrl,
        description: 'URL del sitio web estático',
        exportName: 'S3Wire-WebsiteURL',
      });
    }

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
