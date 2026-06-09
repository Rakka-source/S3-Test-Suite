import os

from config.loader import normalizar_config
from .client_factory import crear_cliente_s3


class S3Manager:
    def __init__(self, config: dict):
        cfg = normalizar_config(config)
        self.access_key = cfg["aws_access_key_id"]
        self.secret_key = cfg["aws_secret_access_key"]
        self.region = cfg["region_name"]
        self.bucket = cfg["bucket_name"]
        self.arn_rol = cfg["arn_rol"]
        self.s3_client = self._crear_cliente()

    def _crear_cliente(self):
        try:
            return crear_cliente_s3(
                self.access_key,
                self.secret_key,
                self.region,
                self.arn_rol,
            )
        except Exception as exc:
            raise Exception(f"Error al crear cliente S3: {exc}") from exc

    def probar_acceso(self) -> str:
        self.s3_client.head_bucket(Bucket=self.bucket)
        return f"✅ Acceso exitoso al bucket: {self.bucket} ({self.region})"

    def listar_archivos(self, prefijo: str = "") -> str:
        paginator = self.s3_client.get_paginator("list_objects_v2")
        pages = paginator.paginate(Bucket=self.bucket, Prefix=prefijo)

        archivos = []
        for page in pages:
            for obj in page.get("Contents", []):
                archivos.append(f"{obj['Key']} ({round(obj['Size'] / 1024, 2)} KB)")

        if not archivos:
            return "Carpeta o bucket vacío."
        return "\n".join(archivos)

    def subir_archivo(self, ruta_local: str, carpeta: str = "", publico: bool = False) -> str:
        nombre_archivo = os.path.basename(ruta_local)
        carpeta = carpeta.strip("/")
        key_s3 = f"{carpeta}/{nombre_archivo}" if carpeta else nombre_archivo

        extra_args = {"ACL": "public-read"} if publico else {}
        self.s3_client.upload_file(ruta_local, self.bucket, key_s3, ExtraArgs=extra_args)

        if publico:
            url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key_s3}"
            return f"✅ Archivo PÚBLICO subido: {key_s3}\nURL: {url}"

        url = self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key_s3},
            ExpiresIn=3600,
        )
        return f"✅ Archivo PRIVADO subido: {key_s3}\nURL Firmada (1h): {url}"

    def eliminar_archivo(self, key_s3: str) -> str:
        self.s3_client.delete_object(Bucket=self.bucket, Key=key_s3)
        return f"✅ Archivo eliminado: {key_s3}"

    def crear_carpeta(self, nombre_carpeta: str) -> str:
        carpeta = nombre_carpeta.strip("/")
        if not carpeta:
            raise ValueError("Debes indicar un nombre de carpeta válido.")

        key_carpeta = f"{carpeta}/"
        self.s3_client.put_object(Bucket=self.bucket, Key=key_carpeta, Body=b"")
        return f"✅ Carpeta creada: {key_carpeta}"

    def eliminar_carpeta(self, nombre_carpeta: str) -> str:
        prefijo = nombre_carpeta.strip("/") + "/"
        paginator = self.s3_client.get_paginator("list_objects_v2")

        objetos_a_borrar = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefijo):
            for obj in page.get("Contents", []):
                objetos_a_borrar.append({"Key": obj["Key"]})

        if not objetos_a_borrar:
            return f"⚠️ La carpeta '{prefijo}' está vacía o no existe."

        for i in range(0, len(objetos_a_borrar), 1000):
            lote = objetos_a_borrar[i : i + 1000]
            self.s3_client.delete_objects(Bucket=self.bucket, Delete={"Objects": lote})

        return f"✅ Carpeta eliminada: {prefijo} ({len(objetos_a_borrar)} objetos)"
