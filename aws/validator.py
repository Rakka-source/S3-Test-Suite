import uuid

import boto3
from botocore.exceptions import ClientError

from config.loader import normalizar_config


class AWSValidator:
    PRUEBAS = (
        ("A", "Cognito (invitado)", "validate_a_cognito_auth"),
        ("B", "Escritura (PutObject)", "validate_b_s3_write"),
        ("C", "Lectura (GetObject)", "validate_c_s3_read"),
        ("D", "Multipart (Create/List/Abort)", "validate_d_s3_multipart"),
        ("E", "Eliminación (DeleteObject)", "validate_e_s3_delete"),
    )

    def __init__(self, config: dict):
        cfg = normalizar_config(config)
        self.region = cfg["region_name"]
        self.identity_pool_id = cfg["identity_pool_id"]
        self.bucket = cfg["bucket_name"]

        aws_access = cfg["aws_access_key_id"]
        aws_secret = cfg["aws_secret_access_key"]

        if not aws_access or not aws_secret or not self.bucket:
            raise ValueError(
                "aws_access_key_id, aws_secret_access_key y bucket_name son obligatorios."
            )

        self.s3_direct_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access,
            aws_secret_access_key=aws_secret,
            region_name=self.region,
        )
        self.cognito = boto3.client(
            "cognito-identity",
            aws_access_key_id=aws_access,
            aws_secret_access_key=aws_secret,
            region_name=self.region,
        )

        self.active_s3_client = self.s3_direct_client
        self.testing_mode = "Credenciales Directas (IAM User)"
        self.test_filename = f"auditoria_seguridad_{uuid.uuid4().hex[:6]}.txt"
        self.multipart_upload_id = None

    def validate_a_cognito_auth(self) -> dict:
        if not self.identity_pool_id:
            return {
                "status": "SKIPPED",
                "message": "Omitido: No se configuró identity_pool_id. Evaluando S3 con credenciales directas.",
            }

        try:
            res_id = self.cognito.get_id(IdentityPoolId=self.identity_pool_id)
            identity_id = res_id.get("IdentityId")

            res_creds = self.cognito.get_credentials_for_identity(IdentityId=identity_id)
            temp_credentials = res_creds["Credentials"]

            self.active_s3_client = boto3.client(
                "s3",
                aws_access_key_id=temp_credentials["AccessKeyId"],
                aws_secret_access_key=temp_credentials["SecretKey"],
                aws_session_token=temp_credentials["SessionToken"],
                region_name=self.region,
            )
            self.testing_mode = "Credenciales Temporales (Cognito Guest)"

            return {
                "status": "SUCCESS",
                "message": f"Login simulado exitoso. Operando bajo IdentityId: {identity_id}",
            }
        except ClientError as exc:
            return {
                "status": "FAILED",
                "message": f"Acceso Denegado en Cognito: {exc.response['Error']['Message']}",
            }

    def validate_b_s3_write(self) -> dict:
        try:
            self.active_s3_client.put_object(
                Bucket=self.bucket,
                Key=self.test_filename,
                Body=b"Prueba de auditoria de seguridad automatizada.",
            )
            return {
                "status": "SUCCESS",
                "message": f"Escritura exitosa en el bucket '{self.bucket}'.",
            }
        except ClientError as exc:
            return {
                "status": "FAILED",
                "message": f"Error PutObject: {exc.response['Error'].get('Message', 'Acceso Denegado')}",
            }

    def validate_c_s3_read(self) -> dict:
        try:
            res = self.active_s3_client.get_object(Bucket=self.bucket, Key=self.test_filename)
            res["Body"].read().decode("utf-8")
            return {"status": "SUCCESS", "message": "Lectura exitosa. Contenido verificado."}
        except ClientError as exc:
            return {
                "status": "FAILED",
                "message": f"Error GetObject: {exc.response['Error'].get('Message', 'Acceso Denegado')}",
            }

    def validate_d_s3_multipart(self) -> dict:
        try:
            multipart_key = f"multipart_{self.test_filename}"
            res_create = self.active_s3_client.create_multipart_upload(
                Bucket=self.bucket,
                Key=multipart_key,
            )
            self.multipart_upload_id = res_create["UploadId"]

            self.active_s3_client.list_parts(
                Bucket=self.bucket,
                Key=multipart_key,
                UploadId=self.multipart_upload_id,
            )
            self.active_s3_client.abort_multipart_upload(
                Bucket=self.bucket,
                Key=multipart_key,
                UploadId=self.multipart_upload_id,
            )
            return {"status": "SUCCESS", "message": "Multipart (Create, List, Abort) permitido."}
        except ClientError as exc:
            return {
                "status": "FAILED",
                "message": f"Error en Multipart: {exc.response['Error'].get('Message', 'Acceso Denegado')}",
            }

    def validate_e_s3_delete(self) -> dict:
        try:
            self.active_s3_client.delete_object(Bucket=self.bucket, Key=self.test_filename)
            return {"status": "SUCCESS", "message": "Archivo de prueba eliminado correctamente."}
        except ClientError as exc:
            return {
                "status": "FAILED",
                "message": f"No se pudo eliminar archivo: {exc.response['Error'].get('Message', 'Acceso Denegado')}",
            }

    def ejecutar_auditoria(self) -> list[dict]:
        resultados = []
        for codigo, nombre, metodo in self.PRUEBAS:
            resultado = getattr(self, metodo)()
            resultado.update({"code": codigo, "name": nombre})
            resultados.append(resultado)
        return resultados

    def formatear_informe(self, resultados: list[dict]) -> str:
        iconos = {"SUCCESS": "✅", "FAILED": "❌", "SKIPPED": "⏭️"}
        lineas = [
            f"--- Auditoría de permisos ({self.testing_mode}) ---",
            f"Bucket: {self.bucket} | Región: {self.region}",
            "",
        ]

        for resultado in resultados:
            icono = iconos.get(resultado["status"], "•")
            lineas.append(
                f"{icono} Prueba {resultado['code']} - {resultado['name']}: {resultado['message']}"
            )

        fallos = sum(1 for r in resultados if r["status"] == "FAILED")
        lineas.append("")
        if fallos:
            lineas.append(f"Resultado: {fallos} prueba(s) fallida(s).")
        else:
            lineas.append("Resultado: Todas las pruebas aplicables pasaron correctamente.")

        return "\n".join(lineas)
