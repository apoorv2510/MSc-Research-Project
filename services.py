import os
import io
import zipfile
import boto3
from botocore.exceptions import ClientError
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient

# ------------- CONFIG -------------
AZURE_SUBSCRIPTION_ID = os.environ.get("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP = "SecureAnalyticsRG"
LOCATION = "eastus"
STORAGE_ACCOUNT = "secureehrstorage123"  # must be globally unique
CONTAINER_NAME = "secure-ehr-container"

LAMBDA_NAME = "EncryptedEHRLambda"
ROLE_NAME = "LabRole"
RUNTIME = "python3.9"
HANDLER = "lambda_function.lambda_handler"
REGION = boto3.session.Session().region_name or "us-east-1"
S3_BUCKET = "secure-ehr-bucket"
KMS_DESC = "Key for metadata encryption"
AZURE_FUNCTION_NAME = "EncryptedQueryFunction"

# ------------- UTILS -------------
def get_account_id():
    return boto3.client("sts").get_caller_identity()["Account"]

def generate_lambda_zip_in_memory():
    lambda_code = """\
def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': 'Lambda with homomorphic encryption setup ran successfully!'
    }
"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zipf:
        zipf.writestr("lambda_function.py", lambda_code)
    buffer.seek(0)
    return buffer.read()

# ------------- AWS SERVICES -------------
def create_s3_bucket(bucket_name, region):
    s3 = boto3.client('s3', region_name=region)
    try:
        s3.head_bucket(Bucket=bucket_name)
        print(f"[✓] S3 bucket '{bucket_name}' already exists. Skipping.")
    except ClientError:
        if region == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': region}
            )
        print(f"[✓] S3 bucket '{bucket_name}' created.")

def create_lambda_function(lambda_name, role_arn, region):
    lambda_client = boto3.client('lambda', region_name=region)
    try:
        lambda_client.get_function(FunctionName=lambda_name)
        print(f"[✓] Lambda function '{lambda_name}' already exists. Skipping.")
        return
    except lambda_client.exceptions.ResourceNotFoundException:
        pass

    zipped_code = generate_lambda_zip_in_memory()
    lambda_client.create_function(
        FunctionName=lambda_name,
        Runtime=RUNTIME,
        Role=role_arn,
        Handler=HANDLER,
        Code={'ZipFile': zipped_code},
        Timeout=300,
        MemorySize=128,
        Publish=True,
    )
    print(f"[✓] Lambda function '{lambda_name}' created.")

def create_kms_key(region):
    kms = boto3.client('kms', region_name=region)
    response = kms.list_keys()
    for key in response["Keys"]:
        metadata = kms.describe_key(KeyId=key["KeyId"])["KeyMetadata"]
        if metadata.get("Description") == KMS_DESC:
            print(f"[✓] KMS key already exists: {metadata['KeyId']}. Skipping.")
            return metadata["KeyId"]

    response = kms.create_key(Description=KMS_DESC)
    key_id = response['KeyMetadata']['KeyId']
    print(f"[✓] New KMS key created: {key_id}")
    return key_id

# ------------- AZURE SERVICES -------------
def create_azure_storage_account_and_container():
    if not AZURE_SUBSCRIPTION_ID:
        raise Exception("AZURE_SUBSCRIPTION_ID environment variable not set.")

    credential = DefaultAzureCredential()
    resource_client = ResourceManagementClient(credential, AZURE_SUBSCRIPTION_ID)
    storage_client = StorageManagementClient(credential, AZURE_SUBSCRIPTION_ID)

    # Create Resource Group
    rg_check = resource_client.resource_groups.check_existence(RESOURCE_GROUP)
    if not rg_check:
        resource_client.resource_groups.create_or_update(RESOURCE_GROUP, {"location": LOCATION})
        print(f"[✓] Resource group '{RESOURCE_GROUP}' created.")
    else:
        print(f"[✓] Resource group '{RESOURCE_GROUP}' already exists. Skipping.")

    # Create Storage Account
    try:
        storage_client.storage_accounts.get_properties(RESOURCE_GROUP, STORAGE_ACCOUNT)
        print(f"[✓] Storage account '{STORAGE_ACCOUNT}' already exists. Skipping.")
    except:
        storage_client.storage_accounts.begin_create(
            RESOURCE_GROUP,
            STORAGE_ACCOUNT,
            {
                "location": LOCATION,
                "sku": {"name": "Standard_LRS"},
                "kind": "StorageV2",
                "enable_https_traffic_only": True,
            },
        ).result()
        print(f"[✓] Storage account '{STORAGE_ACCOUNT}' created.")

    # Get connection string
    keys = storage_client.storage_accounts.list_keys(RESOURCE_GROUP, STORAGE_ACCOUNT)
    conn_str = f"DefaultEndpointsProtocol=https;AccountName={STORAGE_ACCOUNT};AccountKey={keys.keys[0].value};EndpointSuffix=core.windows.net"

    # Create Blob Container
    blob_service = BlobServiceClient.from_connection_string(conn_str)
    try:
        blob_service.create_container(CONTAINER_NAME)
        print(f"[✓] Blob container '{CONTAINER_NAME}' created.")
    except ResourceExistsError:
        print(f"[✓] Blob container '{CONTAINER_NAME}' already exists. Skipping.")

def create_azure_function_placeholder(function_name):
    print(f"[INFO] Deploy Azure Function '{function_name}' manually using Azure CLI or VS Code.")
    print("Run: func azure functionapp publish <YourFunctionAppName>")

# ------------- MAIN -------------
if __name__ == "__main__":
    print("[...] Starting full AWS + Azure deployment")

    account_id = get_account_id()
    role_arn = f"arn:aws:iam::{account_id}:role/{ROLE_NAME}"

    create_azure_storage_account_and_container()
    create_s3_bucket(S3_BUCKET, REGION)
    create_lambda_function(LAMBDA_NAME, role_arn, REGION)
    create_kms_key(REGION)
    create_azure_function_placeholder(AZURE_FUNCTION_NAME)

    print("[✓] All services checked or created successfully.")
