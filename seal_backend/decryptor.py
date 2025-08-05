import tenseal as ts

def decrypt_data(context, encrypted_serialized_list):
    decrypted = []
    for serialized in encrypted_serialized_list:
        enc_vec = ts.bfv_vector_from(context, serialized)
        decrypted.append(enc_vec.decrypt()[0])
    return decrypted
