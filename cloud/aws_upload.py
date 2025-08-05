import boto3

def upload_to_s3(bucket, key, data, binary=False):
    s3 = boto3.client("s3", region_name="us-east-1")

    if isinstance(data, str) and not binary:
        body = data.encode("utf-8")
    elif isinstance(data, bytes) or binary:
        body = data
    else:
        raise TypeError("Unsupported data type for upload")

    s3.put_object(Bucket=bucket, Key=key, Body=body)
    print(f"[✓] Uploaded encrypted data to S3 bucket '{bucket}' as '{key}'")
