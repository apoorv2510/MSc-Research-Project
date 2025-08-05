import tenseal as ts

def square_encrypted_vector(context, encrypted_serialized_list):
    result_serialized = []
    for serialized in encrypted_serialized_list:
        vec = ts.bfv_vector_from(context, serialized)
        squared = vec * vec
        result_serialized.append(squared.serialize())
    return result_serialized
