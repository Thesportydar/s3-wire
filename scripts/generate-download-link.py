#!/usr/bin/env python3
"""
Script para generar links temporales de descarga desde S3.

Este script genera un ID corto aleatorio, crea una URL pre-firmada de S3
para permitir descargas, genera una página HTML personalizada,
y la sube al bucket de hosting estático.
"""

import argparse
import os
import random
import string
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, NoCredentialsError


# Constantes
BASE62_CHARSET = string.ascii_letters + string.digits  # a-zA-Z0-9
DEFAULT_TTL = 21600  # 6 horas
DEFAULT_SHORT_ID_LENGTH = 6

# Template HTML para página de descarga
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>Download File - S3 Wire</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 100%;
            padding: 40px;
            text-align: center;
        }

        h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
        }

        .subtitle {
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }

        .file-info {
            background: #f6f8fa;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
            text-align: left;
        }

        .file-info p {
            color: #555;
            margin: 10px 0;
            font-size: 15px;
        }

        .file-info strong {
            color: #333;
        }

        .download-btn {
            background: #0969da;
            color: white;
            border: none;
            padding: 14px 28px;
            font-size: 16px;
            font-weight: 500;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 20px 0;
            transition: background 0.2s ease;
        }

        .download-btn:hover {
            background: #0550ae;
        }

        .download-btn:active {
            transform: scale(0.98);
        }

        .expires {
            color: #656d76;
            font-size: 14px;
            margin-top: 20px;
        }

        .footer {
            margin-top: 40px;
            color: #656d76;
            font-size: 12px;
        }

        @media (max-width: 600px) {
            .container {
                padding: 30px 20px;
            }

            h1 {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📥 Download Ready</h1>
        <p class="subtitle">Your file is ready to download</p>
        
        <div class="file-info">
            <p><strong>File:</strong> {FILENAME}</p>
            <p class="expires"><strong>Link expires:</strong> {EXPIRATION_TIME}</p>
        </div>
        
        <a href="{PRESIGNED_URL}" class="download-btn" download>
            📥 Download File
        </a>
        
        <p class="footer">
            🔒 Secure connection • Powered by S3-Wire
        </p>
    </div>
</body>
</html>
"""


def generate_short_id(length: int = DEFAULT_SHORT_ID_LENGTH) -> str:
    """
    Genera un identificador corto aleatorio usando base62.
    
    Args:
        length: Longitud del identificador (default: 6)
    
    Returns:
        String aleatorio de la longitud especificada
    """
    return ''.join(random.choices(BASE62_CHARSET, k=length))


def validate_file_exists(s3_client, bucket_name: str, object_key: str) -> bool:
    """
    Valida que el archivo existe en S3 usando head_object.
    
    Args:
        s3_client: Cliente de boto3 para S3
        bucket_name: Nombre del bucket
        object_key: Key del objeto en S3
    
    Returns:
        True si el archivo existe, False en caso contrario
    """
    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def create_presigned_download_url(
    s3_client,
    bucket_name: str,
    object_key: str,
    expiration: int
) -> str:
    """
    Genera una URL pre-firmada para GET desde S3.
    
    Args:
        s3_client: Cliente de boto3 para S3
        bucket_name: Nombre del bucket de origen
        object_key: Key del objeto en S3
        expiration: Tiempo de expiración en segundos
    
    Returns:
        URL pre-firmada como string
    """
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
        return presigned_url
    except ClientError as e:
        print(f"❌ Error al generar URL pre-firmada: {e}", file=sys.stderr)
        sys.exit(1)


def render_html_template(
    presigned_url: str,
    filename: str,
    expiry_date: datetime
) -> str:
    """
    Renderiza el template HTML reemplazando las variables.
    
    Args:
        presigned_url: URL pre-firmada de S3
        filename: Nombre del archivo
        expiry_date: Fecha de expiración
    
    Returns:
        HTML renderizado
    """
    expiration_str = expiry_date.strftime('%Y-%m-%d %H:%M UTC')
    
    rendered = HTML_TEMPLATE.replace('{FILENAME}', filename)
    rendered = rendered.replace('{EXPIRATION_TIME}', expiration_str)
    rendered = rendered.replace('{PRESIGNED_URL}', presigned_url)
    
    return rendered


def upload_html_to_s3(
    s3_client,
    bucket_name: str,
    short_id: str,
    html_content: str
) -> None:
    """
    Sube la página HTML al bucket de hosting.
    
    Args:
        s3_client: Cliente de boto3 para S3
        bucket_name: Nombre del bucket de hosting
        short_id: Identificador corto para la URL
        html_content: Contenido HTML a subir
    """
    object_key = f's/{short_id}/index.html'
    
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=html_content.encode('utf-8'),
            ContentType='text/html; charset=utf-8',
            CacheControl='no-cache, no-store, must-revalidate',
        )
    except ClientError as e:
        print(f"❌ Error al subir HTML a S3: {e}", file=sys.stderr)
        sys.exit(1)


def parse_arguments():
    """
    Parsea argumentos de línea de comandos.
    
    Returns:
        Objeto con los argumentos parseados
    """
    parser = argparse.ArgumentParser(
        description='Genera un link temporal de descarga desde S3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Uso básico
  python generate-download-link.py \\
    --domain up.mydomain.com \\
    --source-bucket my-existing-bucket \\
    --source-key documents/report.pdf \\
    --hosting-bucket up.mydomain.com

  # Con TTL personalizado
  python generate-download-link.py \\
    --domain up.mydomain.com \\
    --source-bucket photos \\
    --source-key vacation/beach.jpg \\
    --hosting-bucket up.mydomain.com \\
    --ttl 3600
        """
    )
    
    parser.add_argument(
        '--domain',
        required=True,
        help='Dominio del bucket de hosting (ej: up.mydomain.com)'
    )
    
    parser.add_argument(
        '--source-bucket',
        required=True,
        help='Nombre del bucket donde está el archivo a compartir'
    )
    
    parser.add_argument(
        '--source-key',
        required=True,
        help='Ruta completa del archivo en el bucket (ej: documents/report.pdf)'
    )
    
    parser.add_argument(
        '--hosting-bucket',
        required=True,
        help='Nombre del bucket de hosting (mismo que domain)'
    )
    
    parser.add_argument(
        '--ttl',
        type=int,
        default=DEFAULT_TTL,
        help=f'Tiempo de vida en segundos (default: {DEFAULT_TTL} = 6 horas)'
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='Región de AWS (default: us-east-1)'
    )
    
    parser.add_argument(
        '--protocol',
        choices=['http', 'https'],
        default='https',
        help='Protocolo para la URL (default: https)'
    )
    
    return parser.parse_args()


def main():
    """
    Función principal del script.
    """
    args = parse_arguments()
    
    # Extraer nombre del archivo
    filename = args.source_key.split('/')[-1]
    
    # Calcular fecha de expiración
    expiry_date = datetime.utcnow() + timedelta(seconds=args.ttl)
    
    # Inicializar cliente de S3
    try:
        s3_client = boto3.client(
            's3',
            region_name=args.region,
            config=Config(signature_version='s3v4')
        )
    except NoCredentialsError:
        print("❌ Error: No se encontraron credenciales de AWS", file=sys.stderr)
        print("Configure credenciales con: aws configure", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error al inicializar cliente S3: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Validar que el archivo existe
    print(f"🔍 Validando que el archivo existe...")
    if not validate_file_exists(s3_client, args.source_bucket, args.source_key):
        print(f"❌ Error: El archivo no existe: s3://{args.source_bucket}/{args.source_key}", file=sys.stderr)
        sys.exit(1)
    
    # Generar short ID
    short_id = generate_short_id()
    
    # Crear URL pre-firmada de descarga
    print("🔗 Generando URL pre-firmada de descarga...")
    presigned_url = create_presigned_download_url(
        s3_client=s3_client,
        bucket_name=args.source_bucket,
        object_key=args.source_key,
        expiration=args.ttl
    )
    
    # Renderizar HTML
    print("🎨 Generando página HTML...")
    html_content = render_html_template(
        presigned_url=presigned_url,
        filename=filename,
        expiry_date=expiry_date
    )
    
    # Subir HTML a S3
    print("☁️  Subiendo página HTML a S3...")
    upload_html_to_s3(
        s3_client=s3_client,
        bucket_name=args.hosting_bucket,
        short_id=short_id,
        html_content=html_content
    )
    
    # Construir URL completa
    short_url = f'{args.protocol}://{args.domain}/s/{short_id}/'
    expiration_str = expiry_date.strftime('%Y-%m-%d %H:%M UTC')
    
    # Mostrar resultado
    print("\n" + "=" * 60)
    print("✅ Download link created successfully!")
    print("=" * 60)
    print(f"\n🔗 Short URL: {short_url}")
    print(f"📄 File: {filename}")
    print(f"⏰ Expires: {expiration_str}")
    print(f"🆔 ID: {short_id}")
    print(f"📦 Source: s3://{args.source_bucket}/{args.source_key}")
    print("\n💡 Share this link to allow file download.")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
