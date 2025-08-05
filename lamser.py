import os
import subprocess
import boto3
import time
import sys
import io

# Fix Windows encoding issues
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# --- CONFIGURATION ---
LAMBDA_NAME = "EncryptedEHRLambda"
ROLE_NAME = "LabRole"  # Make sure this role has Lambda and ECR permissions
ECR_REPO = "tseal-lambda"
AWS_REGION = "us-east-1"  # Change to your region

account_id = boto3.client("sts").get_caller_identity()["Account"]
LAMBDA_ROLE_ARN = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"
ecr_url = f"{account_id}.dkr.ecr.{AWS_REGION}.amazonaws.com/{ECR_REPO}"

# --- Dockerfile Content ---
dockerfile_content = """
FROM public.ecr.aws/lambda/python:3.10

# System dependencies
RUN yum install -y gcc gcc-c++ python3-devel openssl-devel wget make tar gzip

# Install CMake
RUN wget https://github.com/Kitware/CMake/releases/download/v3.26.4/cmake-3.26.4-linux-x86_64.tar.gz && \
    tar xzf cmake-3.26.4-linux-x86_64.tar.gz -C /usr/local --strip-components=1 && \
    rm cmake-3.26.4-linux-x86_64.tar.gz

# 🔧 Install dependencies in correct order
RUN pip install --upgrade pip && \
    pip install numpy && \
    pip install pybind11 tenseal --no-cache-dir

# Copy app code
COPY app.py ${LAMBDA_TASK_ROOT}

# Lambda entry point
CMD ["app.lambda_handler"]

"""

# --- Lambda Handler Code ---
app_code = """
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
"""

# --- Write Files ---
with open("Dockerfile", "w", encoding='utf-8') as f:
    f.write(dockerfile_content)

with open("app.py", "w", encoding='utf-8') as f:
    f.write(app_code)

# --- AWS Setup ---
ecr_client = boto3.client("ecr", region_name=AWS_REGION)
lambda_client = boto3.client("lambda", region_name=AWS_REGION)

# Create ECR repository
try:
    ecr_client.describe_repositories(repositoryNames=[ECR_REPO])
    print("[✓] ECR repository exists")
except ecr_client.exceptions.RepositoryNotFoundException:
    ecr_client.create_repository(repositoryName=ECR_REPO)
    print("[+] Created ECR repository")

# Docker login
print("[🔐] Authenticating Docker to ECR...")
subprocess.run(
    f"aws ecr get-login-password --region {AWS_REGION} | "
    f"docker login --username AWS --password-stdin {account_id}.dkr.ecr.{AWS_REGION}.amazonaws.com",
    shell=True,
    check=True
)

# --- Critical Build Command with Provenance Flag ---
print("[🏗️] Building Docker image with platform and provenance flags...")
try:
    build_cmd = [
        "docker", "build",
        "--platform", "linux/amd64",
        "--provenance=false",  # Key fix for Apple Silicon
        "-t", f"{ecr_url}:latest",
        "."
    ]
    subprocess.run(build_cmd, check=True)
    
    print("[🚢] Pushing image to ECR...")
    subprocess.run(["docker", "push", f"{ecr_url}:latest"], check=True)
except subprocess.CalledProcessError as e:
    print(f"[❌] Docker error: {e}")
    exit(1)

# --- Lambda Deployment ---
print("[🚀] Deploying Lambda function...")
max_retries = 3
retry_delay = 15

for attempt in range(max_retries):
    try:
        # Clean up existing function
        try:
            lambda_client.delete_function(FunctionName=LAMBDA_NAME)
            time.sleep(10)  # Wait for deletion to complete
        except lambda_client.exceptions.ResourceNotFoundException:
            pass

        # Create function
        response = lambda_client.create_function(
            FunctionName=LAMBDA_NAME,
            Role=LAMBDA_ROLE_ARN,
            PackageType="Image",
            Code={"ImageUri": f"{ecr_url}:latest"},
            Timeout=60,
            MemorySize=1024,
            Publish=True
        )
        print(f"[✅] Success! Lambda ARN: {response['FunctionArn']}")
        break
    except Exception as e:
        if attempt == max_retries - 1:
            print(f"[❌] Final attempt failed: {str(e)}")
            exit(1)
        print(f"[⚠️] Attempt {attempt+1} failed, retrying in {retry_delay}s...")
        time.sleep(retry_delay)

print("[🎉] Deployment complete!")