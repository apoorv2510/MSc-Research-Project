# analytics/comparator.py
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
import time
import json

def aes_encrypt_decrypt(data):
    key = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_EAX)
    start = time.time()
    ciphertext, tag = cipher.encrypt_and_digest(json.dumps(data).encode())
    encrypt_time = time.time() - start

    start = time.time()
    decipher = AES.new(key, AES.MODE_EAX, nonce=cipher.nonce)
    plaintext = decipher.decrypt(ciphertext)
    decrypt_time = time.time() - start

    return encrypt_time, decrypt_time

def rsa_encrypt_decrypt(data):
    key = RSA.generate(2048)
    cipher = PKCS1_OAEP.new(key.publickey())
    start = time.time()
    ciphertext = cipher.encrypt(json.dumps(data).encode())
    encrypt_time = time.time() - start

    start = time.time()
    decipher = PKCS1_OAEP.new(key)
    plaintext = decipher.decrypt(ciphertext)
    decrypt_time = time.time() - start

    return encrypt_time, decrypt_time
