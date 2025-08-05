from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

# Hardcoded credentials (make sure to rotate after use or secure them later!)
ACCOUNT_NAME = "secureehrstorage123"
ACCOUNT_KEY = "yySLcb6ZAMmOzRuh4WMWH7tAP8ioCYmKdTePTXVOI5R3eO+5vdSoJm5HVM2HSTkTFLEuGoYL+2/8+AStdleakg=="

CONNECTION_STRING = f"DefaultEndpointsProtocol=https;AccountName={ACCOUNT_NAME};AccountKey={ACCOUNT_KEY};EndpointSuffix=core.windows.net"

def upload_to_blob(container_name, blob_name, data):
    try:
        # Connect to Azure Blob Service
        blob_service_client = BlobServiceClient.from_connection_string(CONNECTION_STRING)

        # Create container if it doesn't exist
        try:
            blob_service_client.create_container(container_name)
            print(f"[✓] Created container: {container_name}")
        except Exception:
            print(f"[i] Container '{container_name}' already exists.")

        # Get blob client
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        # Upload data
        blob_client.upload_blob(data, overwrite=True)
        print(f"[✓] Uploaded encrypted data to Azure container '{container_name}' as '{blob_name}'")
    
    except Exception as e:
        print(f"[✗] Azure Blob upload failed: {e}")
