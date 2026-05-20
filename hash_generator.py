import os
from werkzeug.security import generate_password_hash

# Ketik username dan password baru Anda di sini
NEW_USER = "admin"
NEW_PASS = "edogawa47" 

DATA_FOLDER = 'data'
CREDENTIALS_FILE = os.path.join(DATA_FOLDER, 'credentials.txt')

# Generate enkripsi password baru
hashed_password = generate_password_hash(NEW_PASS)

# Tulis otomatis ke file credentials.txt
os.makedirs(DATA_FOLDER, exist_ok=True)
with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
    f.write(f"USERNAME={NEW_USER}\nHASHED_PASSWORD={hashed_password}\n")

print("Password baru berhasil dienkripsi dan disimpan ke data/credentials.txt!")