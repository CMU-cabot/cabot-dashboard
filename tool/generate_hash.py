import bcrypt
import json

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

users = [
    {"id": "user1", "password": "password1"},
    {"id": "user2", "password": "password2"}
]

hashed_users = [{"id": u["id"], "password_hash": hash_password(u["password"])} for u in users]

with open('users.json', 'w') as f:
    json.dump({"users": hashed_users}, f, indent=2)

print("users.json has been updated with bcrypt hashes.")