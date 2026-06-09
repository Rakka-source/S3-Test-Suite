import json
from pathlib import Path

CONFIG_FILE = Path("config_s3.json")


def normalizar_config(config: dict) -> dict:
    """Unifica claves de config_s3.json y del validador de permisos."""
    return {
        "aws_access_key_id": config.get("aws_access_key_id") or config.get("AWS_ACCESS_KEY", ""),
        "aws_secret_access_key": config.get("aws_secret_access_key") or config.get("AWS_SECRET_KEY", ""),
        "region_name": config.get("region_name") or config.get("REGION", "us-east-1"),
        "bucket_name": config.get("bucket_name") or config.get("NOMBRE_BUCKET", ""),
        "arn_rol": config.get("ARN_ROL", ""),
        "identity_pool_id": config.get("identity_pool_id") or config.get("IDENTITY_POOL_ID"),
    }


def cargar_configuracion(ruta: Path | str = CONFIG_FILE) -> dict:
    ruta = Path(ruta)
    with open(ruta, "r", encoding="utf-8") as archivo:
        return json.load(archivo)
