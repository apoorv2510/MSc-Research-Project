
import json
import base64
import boto3
import tenseal as ts

s3 = boto3.client("s3")

def lambda_handler(event, context):
    try:
        bucket = event.get("s3_bucket")
        payload_key = event.get("encrypted_payload_key")
        context_key = event.get("seal_context_key")

        if not (bucket and payload_key and context_key):
            return {
                "statusCode": 400,
                "error": "Missing required S3 keys"
            }

        # Download encrypted payload from S3
        payload_obj = s3.get_object(Bucket=bucket, Key=payload_key)
        encrypted_payload_b64 = payload_obj["Body"].read().decode("utf-8")

        # Download context (in bytes)
        context_obj = s3.get_object(Bucket=bucket, Key=context_key)
        context_bytes = context_obj["Body"].read()

        # Restore context
        context = ts.context_from(context_bytes)

        # Decode and decrypt
        encrypted_bytes = base64.b64decode(encrypted_payload_b64)
        ckks_vector = ts.ckks_vector_from(context, encrypted_bytes)
        decrypted = ckks_vector.decrypt()

        return {
            "statusCode": 200,
            "decrypted_result": decrypted[:10]  # Only return first 10 values
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "error": str(e)
        }
