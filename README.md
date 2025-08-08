
# **Secure Multi-Cloud Healthcare Analytics with Homomorphic Encryption (CKKS)**

## 📌 Overview

This project implements a **privacy-preserving analytics pipeline** for sensitive healthcare datasets using **Homomorphic Encryption (HE)** with the **CKKS scheme**.
It enables **encrypted computation** on patient data without exposing plaintext values, while storing and processing data across **AWS** and **Azure** cloud environments.

The pipeline:

* Encrypts data locally using **TenSEAL CKKS**.
* Uploads encrypted payloads and encryption context to **AWS S3** and **Azure Blob Storage**.
* Uses **AWS Lambda** for processing encrypted data (or decryption in controlled environments).
* Compares performance with **AES encryption**.
* Generates **execution metrics** and visualizes them in a **Streamlit dashboard**.

---

## 🚀 Features

* **CKKS Homomorphic Encryption** – Floating-point encryption for real-valued medical data.
* **Multi-Cloud Storage** – Redundant uploads to AWS S3 and Azure Blob.
* **AWS Lambda Processing** – Serverless compute for encrypted data workflows.
* **AES Benchmarking** – Symmetric encryption baseline for performance comparison.
* **Automated Metrics Logging** – Tracks execution time for each pipeline step.
* **Visualization Dashboard** – Streamlit-powered charts for encryption performance.

---

## 🗂 Project Structure

```
.
├── main.py                  # Main pipeline script
├── app.py                   # AWS Lambda handler
├── encryptor.py              # CKKS encryption helper
├── lamser.py                 # Docker + Lambda deployment
├── services.py               # AWS & Azure resource provisioning
├── dashboard.py              # Streamlit visualization dashboard
├── requirements.txt          # Python dependencies
├── encryption_metrics.json   # Metrics output (generated)
└── encryption_metrics_report.pdf # Performance charts (generated)
```

> **Note:** Files like `decryptor.py`, `evaluator.py`, and `seal_context.py` are BFV-based from earlier experiments and not used in the current CKKS flow.

---

## ⚙️ Prerequisites

### **Local Machine**

* Python **3.10+**
* Docker (for Lambda container image builds)
* AWS CLI (v2) – Configured with access to S3, Lambda, ECR, and KMS
* Azure CLI – Logged in and authorized
* MIMIC-III Demo Dataset – `DRGCODES.csv`

### **Python Dependencies**

Install from `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## 🔑 Configuration

Edit `main.py` to set:

```python
KMS_KEY_ID = "arn:aws:kms:REGION:ACCOUNT:key/KEY-ID"
LAMBDA_FUNCTION_NAME = "EncryptedEHRLambda"
file_path = "/path/to/DRGCODES.csv"
```

Also ensure:

* The `encryptor.py` file is in the Python import path.
* AWS credentials are configured for your account.
* Azure storage account and container are created.

---

## 📦 Deployment

### **1. Build and Deploy Lambda**

```bash
python lamser.py
```

* Builds Docker image
* Pushes to AWS ECR
* Creates/updates Lambda function

### **2. Provision Cloud Resources**

```bash
python services.py
```

* Creates S3 bucket
* Creates Azure container
* Optionally provisions KMS key

---

## ▶️ Running the Pipeline

```bash
python main.py
```

**Pipeline Steps:**

1. Create CKKS context with TenSEAL.
2. Load and preprocess MIMIC-III dataset.
3. Encrypt data using CKKS.
4. Serialize and upload encrypted payload to AWS S3 & Azure Blob.
5. Encrypt keys with AWS KMS.
6. Invoke AWS Lambda for processing.
7. Compare with AES encryption.
8. Log metrics and generate performance charts.

---

## 📊 Visualizing Metrics

Run:

```bash
streamlit run dashboard.py
```

* **Bar Chart:** Time taken per pipeline step
* **Grouped Chart:** CKKS vs AES vs Upload vs KMS
* **Table:** Raw metrics data

---

## 🔒 Security Notes

* To **avoid sending the secret key to the cloud**, set:

  ```python
  context.serialize(save_secret_key=False)
  ```

  and perform decryption only locally.
* Use IAM least privilege for Lambda and S3 access.
* Enable S3 encryption with SSE-KMS.
* Rotate KMS keys periodically.

---

## 📄 License

This project is provided for **educational and research purposes**.
Ensure compliance with **HIPAA/GDPR** when using real patient data.

---


