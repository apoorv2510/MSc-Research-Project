import json
import base64
import os
import time
import math
import boto3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import tenseal as ts
from seal_backend import encryptor
from key_management import key_gen
from cloud import aws_upload, azure_upload
from analytics.mimic_preprocessor import load_and_prepare_mimic
from cryptography.fernet import Fernet

# --- AWS Setup ---
KMS_KEY_ID = "arn:aws:kms:us-east-1:324362263667:key/2f8de86b-4c1f-45d7-b4bf-a8b9022ee058"
LAMBDA_FUNCTION_NAME = "EncryptedEHRLambda"
kms_client = boto3.client("kms", region_name="us-east-1")
lambda_client = boto3.client("lambda", region_name="us-east-1")

# --- Metric Tracker ---
metrics = {}
def track(label, start_time):
    metrics[label] = round(time.time() - start_time, 4)

# --- Recursive Base64 Encoding ---
def encode_bytes_recursive(obj):
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    elif isinstance(obj, dict):
        return {k: encode_bytes_recursive(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [encode_bytes_recursive(i) for i in obj]
    return obj

def calculate_entropy(data):
    from collections import Counter
    prob = [v / len(data) for v in Counter(data).values()]
    return -sum(p * math.log2(p) for p in prob)

# ✅ Step 1: Create SEAL context
def create_context():
    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=8192,
        coeff_mod_bit_sizes=[60, 40, 40, 60]
    )
    context.global_scale = 2**40
    context.generate_galois_keys()
    context.generate_relin_keys()
    return context

start = time.time()
context = create_context()
track("create_context", start)

# Step 2: Load and prepare MIMIC data
file_path = "D:\\Research\\mimic-iii-clinical-database-demo-1.4\\mimic-iii-clinical-database-demo-1.4\\DRGCODES.csv"
if not os.path.exists(file_path):
    raise FileNotFoundError(f"[❌] File not found: {file_path}")
start = time.time()
mimic_data = load_and_prepare_mimic(file_path)
track("load_prepare_data", start)
print("[✓] Prepared data:", mimic_data)

# Step 3: Encrypt with HE using TenSEAL
start = time.time()
encrypted_he = encryptor.encrypt_data(context, mimic_data)
track("he_encrypt", start)
print("[✓] Encrypted with HE (type):", type(encrypted_he))

# Step 4: Serialize encrypted data (TenSEAL -> bytes)
try:
    encrypted_bytes = encrypted_he.serialize()
except AttributeError:
    raise TypeError("Encrypted HE data does not support serialization. Ensure it's a TenSEAL CKKSVector.")
serialized_he = base64.b64encode(encrypted_bytes).decode("utf-8")
print(f"[i] Encrypted payload size (base64): {len(serialized_he)} characters")
print(f"[i] Entropy of encrypted payload: {round(calculate_entropy(encrypted_bytes), 4)}")

# Step 5: Encrypt dummy HE key with KMS (for metric demo)
start = time.time()
dummy_he_key = base64.b64encode(b"fake_he_secret_key_for_metrics").decode('utf-8')
kms_encrypted_he_key = kms_client.encrypt(
    KeyId=KMS_KEY_ID,
    Plaintext=dummy_he_key.encode()
)['CiphertextBlob']
track("kms_encrypt_dummy_HE_key", start)
print("[✓] Simulated HE secret key encrypted with KMS")

# Step 6: Upload to AWS and Azure
start = time.time()
aws_upload.upload_to_s3("secure-ehr-bucket", "encrypted_data_HE.json", serialized_he)
track("upload_s3_HE", start)

start = time.time()
azure_upload.upload_to_blob("secure-container", "encrypted_data_HE.json", serialized_he)
track("upload_azure_HE", start)

# ✅ Step 7: Upload serialized context to S3 (binary mode)
context_bytes = context.serialize(save_secret_key=True)
context_key = "seal_context.bin"
aws_upload.upload_to_s3("secure-ehr-bucket", context_key, context_bytes, binary=True)
print(f"[i] Context size (bytes): {len(context_bytes)}")

# ✅ Step 8: Invoke Lambda for HE decryption (S3 reference pattern)
lambda_payload = {
    "s3_bucket": "secure-ehr-bucket",
    "encrypted_payload_key": "encrypted_data_HE.json",
    "seal_context_key": context_key
}

start = time.time()
lambda_response = lambda_client.invoke(
    FunctionName=LAMBDA_FUNCTION_NAME,
    InvocationType='RequestResponse',
    Payload=json.dumps(lambda_payload)
)
track("lambda_invoke", start)

# Step 9: Robust Lambda response handling
try:
    payload_stream = lambda_response.get('Payload')
    if payload_stream is None:
        print("[❌] Lambda response missing Payload field.")
        exit(1)

    lambda_result = json.load(payload_stream)

    status_code = lambda_response.get("StatusCode", 0)
    if status_code != 200:
        print(f"[❌] Lambda returned HTTP {status_code}")
        print("Raw Lambda response:", lambda_result)
        exit(1)

    decrypted_he_result = lambda_result.get("decrypted_result")
    error_message = lambda_result.get("error")

    if decrypted_he_result:
        print("[✓] HE decrypted result from Lambda:")
        if isinstance(decrypted_he_result, list):
            print(" - First 10 values:", decrypted_he_result[:10])
        elif isinstance(decrypted_he_result, dict):
            for k, v in decrypted_he_result.items():
                print(f"   • {k}: {v}")
        else:
            print(" - Result:", decrypted_he_result)
    elif error_message:
        print("[❌] Lambda returned an error:")
        print("Error:", error_message)
    else:
        print("[❌] Lambda returned successfully but with no decrypted_result or error field.")
        print("Full Lambda result:", lambda_result)
        exit(1)

except json.JSONDecodeError as je:
    print(f"[💥] Failed to decode Lambda response JSON: {str(je)}")
    print("Raw Payload:", lambda_response.get("Payload"))
    exit(1)
except Exception as e:
    print(f"[💥] Unexpected error while processing Lambda response: {str(e)}")
    exit(1)

# Step 10: AES Encryption for Comparison
print("\n[🔍] Now comparing with AES-style encryption...\n")
aes_key = Fernet.generate_key()
cipher = Fernet(aes_key)
mimic_str = json.dumps(mimic_data).encode('utf-8')

start = time.time()
aes_encrypted = cipher.encrypt(mimic_str)
track("aes_encrypt", start)

start = time.time()
aes_decrypted = json.loads(cipher.decrypt(aes_encrypted).decode('utf-8'))
track("aes_decrypt", start)

print("[✓] AES encrypted length:", len(aes_encrypted))
print("[✓] AES decrypted output:", aes_decrypted[:10], "...")

# Step 11: Upload AES encrypted data (binary=True)
start = time.time()
aws_upload.upload_to_s3("secure-ehr-bucket", "encrypted_data_AES.json", aes_encrypted, binary=True)
track("upload_s3_AES", start)

# Step 12: Encrypt AES key with AWS KMS
start = time.time()
kms_encrypted_key = kms_client.encrypt(
    KeyId=KMS_KEY_ID,
    Plaintext=aes_key
)['CiphertextBlob']
track("kms_encrypt_key", start)
print("[✓] AES key encrypted with KMS")

# Step 13: Save metrics
with open("encryption_metrics.json", "w") as f:
    json.dump(metrics, f, indent=2)
print("[✓] Metrics exported to encryption_metrics.json")

# Step 14: Generate charts
def generate_metric_charts(metrics_dict):
    labels = list(metrics_dict.keys())
    values = list(metrics_dict.values())

    with PdfPages("encryption_metrics_report.pdf") as pdf:
        plt.figure(figsize=(12, 6))
        plt.bar(labels, values)
        plt.xlabel('Operation Step')
        plt.ylabel('Time (seconds)')
        plt.title('Encryption and Upload Execution Time')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, axis='y')
        plt.tight_layout()
        plt.savefig("encryption_metrics_bar.png")
        pdf.savefig()
        plt.close()

        plt.figure(figsize=(10, 8))
        plt.barh(labels, values)
        plt.xlabel('Time (seconds)')
        plt.title('Time Taken by Each Operation Step')
        plt.grid(True, axis='x')
        plt.tight_layout()
        plt.savefig("encryption_metrics_horizontal.png")
        pdf.savefig()
        plt.close()

        grouped = {
            "HE Ops": metrics.get("he_encrypt", 0),
            "AES Ops": metrics.get("aes_encrypt", 0) + metrics.get("aes_decrypt", 0),
            "Upload Time": metrics.get("upload_s3_HE", 0) + metrics.get("upload_azure_HE", 0) + metrics.get("upload_s3_AES", 0),
            "KMS Encryption": metrics.get("kms_encrypt_key", 0) + metrics.get("kms_encrypt_dummy_HE_key", 0),
            "Lambda Compute": metrics.get("lambda_invoke", 0),
            "Data Prep": metrics.get("load_prepare_data", 0)
        }

        plt.figure(figsize=(10, 6))
        plt.bar(grouped.keys(), grouped.values())
        plt.ylabel("Total Time (s)")
        plt.title("Grouped Operation Times")
        plt.xticks(rotation=30, ha='right')
        plt.grid(True, axis='y')
        plt.tight_layout()
        plt.savefig("encryption_metrics_grouped.png")
        pdf.savefig()
        plt.close()

    print("[📊] Charts and PDF report generated (encryption_metrics_report.pdf)")

generate_metric_charts(metrics)
print("[🏁] Pipeline complete.")

def verify_decryption(original, decrypted):
    print("\n[🔍] Verifying decrypted HE output against original data...")
    original_float = [float(x) for x in original]
    if all(abs(o - d) < 1e-3 for o, d in zip(original_float, decrypted)):
        print("[✅] Decryption verified: Decrypted HE output matches original data (within tolerance).")
    else:
        print("[❌] Decryption mismatch detected!")
        for i, (o, d) in enumerate(zip(original_float, decrypted)):
            if abs(o - d) >= 1e-3:
                print(f" - Index {i}: Original={o}, Decrypted={d}")

# Call it like this right after Lambda output is received:
verify_decryption(mimic_data, decrypted_he_result)
