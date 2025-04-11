import cryptography.fernet

class DataEncryptor:
    def __init__(self, encryption_key: str):
        try:
            self.key = cryptography.fernet.Fernet.generate_key() if encryption_key is None else encryption_key.encode()
            self.cipher = cryptography.fernet.Fernet(self.key)
        except ImportError:
            raise ImportError("Cryptography library not found. Please install it using 'pip install cryptography'")

    def encrypt_data(self, data: str) -> str:
        try:
            encrypted_data = self.cipher.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            raise ValueError(f"Error encrypting data: {e}")

    def decrypt_data(self, encrypted_data: str) -> str:
        try:
            decrypted_data = self.cipher.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            raise ValueError(f"Error decrypting data: {e}")