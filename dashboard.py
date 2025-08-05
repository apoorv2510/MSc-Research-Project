import json
import os  # <-- Add this line
import base64
import time
import math
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Load encryption metrics
with open("encryption_metrics.json") as f:
    metrics = json.load(f)

st.title("🔐 Secure Encryption Pipeline Dashboard")

# Metric table
st.subheader("📊 Operation Time Metrics")
df_metrics = pd.DataFrame(metrics.items(), columns=["Operation", "Time (s)"])
st.dataframe(df_metrics.style.format({"Time (s)": "{:.4f}"}))

# Bar chart - raw times
st.subheader("📈 Execution Time by Operation")
fig1, ax1 = plt.subplots(figsize=(10, 5))
ax1.bar(df_metrics["Operation"], df_metrics["Time (s)"])
ax1.set_xticklabels(df_metrics["Operation"], rotation=45, ha='right')
ax1.set_ylabel("Time (seconds)")
ax1.set_title("Individual Operation Execution Times")
st.pyplot(fig1)

# Grouped operations
grouped = {
    "HE Ops": metrics.get("he_encrypt", 0),
    "AES Ops": metrics.get("aes_encrypt", 0) + metrics.get("aes_decrypt", 0),
    "Upload Time": metrics.get("upload_s3_HE", 0) + metrics.get("upload_azure_HE", 0) + metrics.get("upload_s3_AES", 0),
    "KMS Encryption": metrics.get("kms_encrypt_key", 0) + metrics.get("kms_encrypt_dummy_HE_key", 0),
    "Lambda Compute": metrics.get("lambda_invoke", 0),
    "Data Prep": metrics.get("load_prepare_data", 0)
}

st.subheader("📦 Grouped Operation Time Breakdown")
df_grouped = pd.DataFrame(grouped.items(), columns=["Group", "Time (s)"])
fig2, ax2 = plt.subplots(figsize=(8, 4))
ax2.bar(df_grouped["Group"], df_grouped["Time (s)"], color="skyblue")
ax2.set_ylabel("Total Time (s)")
ax2.set_title("Grouped Processing Time")
st.pyplot(fig2)

# Optional: Load decrypted HE result
if os.path.exists("decrypted_HE.json"):
    with open("decrypted_HE.json") as f:
        decrypted_data = json.load(f)

    st.subheader("🔓 Sample Decrypted HE Output")
    st.write("First 10 values:")
    st.json(decrypted_data[:10])

st.caption("© Secure HE Multi-cloud Pipeline • Built with TenSEAL, AWS, Azure, and Streamlit")
