# encryptor.py

import tenseal as ts

def encrypt_data(context, data):
    # Ensure data is a list of floats or integers
    flat_data = [float(x) for x in data[:100]]  # Optionally limit
    enc_vec = ts.ckks_vector(context, flat_data)
    return enc_vec
