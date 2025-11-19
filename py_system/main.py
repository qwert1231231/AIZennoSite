import os
import json
import hashlib
import secrets
from typing import Optional, Tuple

# Data file located in project's data/ folder
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILE = os.path.join(BASE_DIR, 'data', 'someone.json')


def _ensure_data_file():
    if not os.path.exists(os.path.dirname(DATA_FILE)):
        os.makedirs(os.path.dirname(DATA_FILE))
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({"users": []}, f, indent=2)


def _load():
    _ensure_data_file()
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save(data):
    _ensure_data_file()
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def _hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    # Use PBKDF2-HMAC-SHA256 with per-user random salt
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100_000)
    return dk.hex(), salt


def find_user(username: str) -> Optional[dict]:
    data = _load()
    for u in data.get('users', []):
        if u.get('username') == username:
            return u
    return None


def create_user(username: str, password: str, name: str, email: str = '') -> Tuple[bool, str]:
    data = _load()
    if find_user(username):
        return False, 'Username already exists'
    pwd_hash, salt = _hash_password(password)
    user = {"username": username, "password": pwd_hash, "salt": salt, "name": name, "email": email}
    data.setdefault('users', []).append(user)
    _save(data)
    return True, ''


def verify_user(username: str, password: str) -> Optional[dict]:
    u = find_user(username)
    if not u:
        return None
    salt = u.get('salt')
    if not salt:
        # legacy fallback: stored password may be plain sha1 hex
        legacy = hashlib.sha1(password.encode('utf-8')).hexdigest()
        if u.get('password') == legacy:
            return {"username": u.get('username'), "name": u.get('name'), "email": u.get('email', '')}
        return None
    pwd_hash, _ = _hash_password(password, salt)
    if u.get('password') == pwd_hash:
        return {"username": u.get('username'), "name": u.get('name'), "email": u.get('email', '')}
    return None


def update_user(username: str, updates: dict) -> Tuple[bool, str]:
    data = _load()
    users = data.setdefault('users', [])
    for u in users:
        if u.get('username') == username:
            # allowed updates: name, email
            if 'name' in updates:
                u['name'] = updates['name']
            if 'email' in updates:
                u['email'] = updates['email']
            _save(data)
            return True, ''
    return False, 'User not found'


def change_password(username: str, current_password: str, new_password: str) -> Tuple[bool, str]:
    u = find_user(username)
    if not u:
        return False, 'User not found'
    salt = u.get('salt')
    if not salt:
        return False, 'Invalid user record'
    current_hash, _ = _hash_password(current_password, salt)
    if current_hash != u.get('password'):
        return False, 'Current password incorrect'
    new_hash, new_salt = _hash_password(new_password)
    u['password'] = new_hash
    u['salt'] = new_salt
    data = _load()
    _save(data)
    return True, ''
