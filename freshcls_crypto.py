import cryptography
from cryptography.fernet import Fernet

def encrypto(origin_cd):
        
    key = Fernet.generate_key()

    print(f'synchronize_key : {key}')

    fernet = Fernet(key)
    encrypt_str = fernet.encrypt(bytes(origin_cd, 'ascii'))

    return encrypt_str