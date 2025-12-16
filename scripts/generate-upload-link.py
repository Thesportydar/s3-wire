#!/usr/bin/env python3
"""
Script para generar links temporales de upload a S3.

Este script genera un ID corto aleatorio, crea una URL pre-firmada de S3
para permitir uploads, genera una página HTML personalizada desde un template,
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
from botocore.exceptions import ClientError, NoCredentialsError


# Constantes
BASE62_CHARSET = string.ascii_letters + string.digits  # a-zA-Z0-9
DEFAULT_TTL = 86400  # 24 horas
DEFAULT_MAX_SIZE = 100 * 1024 * 1024  # 100 MB
DEFAULT_SHORT_ID_LENGTH = 6
TEMPLATE_DIR = Path(__file__).parent.parent / 'templates'
TEMPLATE_FILE = TEMPLATE_DIR / 'upload-page.html'


def generate_short_id(length: int = DEFAULT_SHORT_ID_LENGTH) -> str:
    """
    Genera un identificador corto aleatorio usando base62.
    
    Args:
        length: Longitud del identificador (default: 6)
    
    Returns:
        String aleatorio de la longitud especificada
    """
    return ''.join(random.choices(BASE62_CHARSET, k=length))


def create_presigned_url(
    s3_client,
    bucket_name: str,
    object_key: str,
    expiration: int,
    max_size: Optional[int] = None,
    content_type: Optional[str] = None
) -> str:
    """
    Genera una URL pre-firmada para PUT a S3.
    
    Args:
        s3_client: Cliente de boto3 para S3
        bucket_name: Nombre del bucket de almacenamiento
        object_key: Key del objeto en S3
        expiration: Tiempo de expiración en segundos
        max_size: Tamaño máximo del archivo en bytes (opcional, validado en cliente)
        content_type: Content-Type permitido (opcional, validado en cliente)
    
    Returns:
        URL pre-firmada como string
    
    Nota:
        Las restricciones de tamaño y tipo se validan en el cliente (JavaScript).
        Para restricciones del lado del servidor, usar generate_presigned_post.
    """
    params = {
        'Bucket': bucket_name,
        'Key': object_key,
    }
    
    try:
        # Generar URL pre-firmada para PUT
        # Nota: generate_presigned_url no soporta conditions complejas
        # Las validaciones de tamaño y tipo se hacen en el cliente
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params=params,
            ExpiresIn=expiration,
        )
        return presigned_url
    except ClientError as e:
        print(f"❌ Error al generar URL pre-firmada: {e}", file=sys.stderr)
        sys.exit(1)


def load_template() -> str:
    """
    Carga el template HTML desde archivo.
    
    Returns:
        Contenido del template como string
    """
    if not TEMPLATE_FILE.exists():
        print(f"❌ Error: Template no encontrado en {TEMPLATE_FILE}", file=sys.stderr)
        sys.exit(1)
    
    try:
        with open(TEMPLATE_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except IOError as e:
        print(f"❌ Error al leer template: {e}", file=sys.stderr)
        sys.exit(1)


def render_template(
    template: str,
    presigned_url: str,
    max_file_size: int,
    allowed_types: str,
    expiry_date: datetime
) -> str:
    """
    Renderiza el template HTML reemplazando las variables.
    
    Args:
        template: Contenido del template
        presigned_url: URL pre-firmada de S3
        max_file_size: Tamaño máximo en bytes
        allowed_types: Tipos MIME permitidos
        expiry_date: Fecha de expiración
    
    Returns:
        HTML renderizado
    """
    replacements = {
        '{PRESIGNED_URL}': presigned_url,
        '{MAX_FILE_SIZE}': str(max_file_size),
        '{ALLOWED_TYPES}': allowed_types,
        '{EXPIRY_DATE}': expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC'),
    }
    
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    
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
    object_key = f'u/{short_id}/index.html'
    
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
        description='Genera un link temporal de upload a S3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Uso básico
  python generate-upload-link.py \\
    --domain up.mydomain.com \\
    --storage-bucket my-storage-bucket \\
    --hosting-bucket up.mydomain.com

  # Con opciones personalizadas
  python generate-upload-link.py \\
    --domain up.mydomain.com \\
    --storage-bucket my-storage-bucket \\
    --hosting-bucket up.mydomain.com \\
    --ttl 3600 \\
    --max-size 52428800 \\
    --allowed-types "image/*,application/pdf"
        """
    )
    
    parser.add_argument(
        '--domain',
        required=True,
        help='Dominio del bucket de hosting (ej: up.mydomain.com)'
    )
    
    parser.add_argument(
        '--storage-bucket',
        required=True,
        help='Nombre del bucket de almacenamiento'
    )
    
    parser.add_argument(
        '--hosting-bucket',
        required=True,
        help='Nombre del bucket de hosting'
    )
    
    parser.add_argument(
        '--ttl',
        type=int,
        default=DEFAULT_TTL,
        help=f'Tiempo de vida en segundos (default: {DEFAULT_TTL} = 24h)'
    )
    
    parser.add_argument(
        '--max-size',
        type=int,
        default=DEFAULT_MAX_SIZE,
        help=f'Tamaño máximo de archivo en bytes (default: {DEFAULT_MAX_SIZE} = 100MB)'
    )
    
    parser.add_argument(
        '--allowed-types',
        default='*/*',
        help='Tipos MIME permitidos separados por coma (default: */*)'
    )
    
    parser.add_argument(
        '--filename',
        default=None,
        help='Nombre del archivo en S3 (default: se genera automáticamente)'
    )
    
    parser.add_argument(
        '--region',
        default=None,
        help='Región de AWS (default: región por defecto de AWS CLI)'
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
    
    # Generar ID corto
    short_id = generate_short_id()
    
    # Generar nombre de archivo si no se especificó
    filename = args.filename or f'upload-{short_id}'
    object_key = f'inbox/{filename}'
    
    # Calcular fecha de expiración
    expiry_date = datetime.utcnow() + timedelta(seconds=args.ttl)
    
    # Inicializar cliente de S3
    try:
        s3_client = boto3.client('s3', region_name=args.region)
    except NoCredentialsError:
        print("❌ Error: No se encontraron credenciales de AWS", file=sys.stderr)
        print("Configure credenciales con: aws configure", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error al inicializar cliente S3: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Crear URL pre-firmada
    print("🔗 Generando URL pre-firmada...")
    presigned_url = create_presigned_url(
        s3_client=s3_client,
        bucket_name=args.storage_bucket,
        object_key=object_key,
        expiration=args.ttl,
        max_size=args.max_size,
    )
    
    # Cargar template
    print("📄 Cargando template HTML...")
    template = load_template()
    
    # Renderizar template
    print("🎨 Renderizando página HTML...")
    html_content = render_template(
        template=template,
        presigned_url=presigned_url,
        max_file_size=args.max_size,
        allowed_types=args.allowed_types,
        expiry_date=expiry_date,
    )
    
    # Subir HTML a S3
    print("☁️  Subiendo página HTML a S3...")
    upload_html_to_s3(
        s3_client=s3_client,
        bucket_name=args.hosting_bucket,
        short_id=short_id,
        html_content=html_content,
    )
    
    # Construir URL completa
    upload_link = f'{args.protocol}://{args.domain}/u/{short_id}/'
    
    # Mostrar resultado
    print("\n" + "=" * 60)
    print("✅ Link generado exitosamente!")
    print("=" * 60)
    print(f"\n🔗 Link de upload: {upload_link}")
    print(f"⏰ Válido hasta: {expiry_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"🆔 ID: {short_id}")
    print(f"📦 Archivo se guardará en: s3://{args.storage_bucket}/{object_key}")
    print(f"📏 Tamaño máximo: {args.max_size / (1024 * 1024):.1f} MB")
    print(f"📄 Tipos permitidos: {args.allowed_types}")
    print("\n💡 Comparte este link con el usuario para que suba su archivo.")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
