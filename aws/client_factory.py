import boto3


def crear_cliente_s3(access_key: str, secret_key: str, region: str, arn_rol: str = ""):
    """Crea un cliente S3 con credenciales directas o asumiendo un rol IAM."""
    if arn_rol:
        sts = boto3.client(
            "sts",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        asumido = sts.assume_role(RoleArn=arn_rol, RoleSessionName="S3AppSession")
        cred = asumido["Credentials"]
        return boto3.client(
            "s3",
            aws_access_key_id=cred["AccessKeyId"],
            aws_secret_access_key=cred["SecretAccessKey"],
            aws_session_token=cred["SessionToken"],
            region_name=region,
        )

    return boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
