import requests
import tkinter as tk
from tkinter import simpledialog, messagebox
import supabase
import os
import json
import hashlib
import uuid
import keyring
import sys
import ctypes

# AUTH_URL = "http://127.0.0.1:5000/login"

# def request_token():
#     root = tk.Tk()
#     root.withdraw()

#     email = simpledialog.askstring("Login", "Enter your email:")
#     if email is None:
#         return None
#     password = simpledialog.askstring("Login", "Enter your password:", show="*")
#     if password is None:
#         return None

#     try:
#         response = requests.post(AUTH_URL, json={"email": email, "password": password})
#         if response.status_code == 200:
#             token = response.json().get("token")
#             return token
#         else:
#             messagebox.showerror("Error", f"Login failed: {response.text}")
#     except Exception as e:
#         messagebox.showerror("Error", f"Connection error: {str(e)}")

#     return None
if getattr(sys, 'frozen', False):
    # Якщо .exe — беремо директорію з .exe (onedir launcher.exe)
    base_dir = os.path.dirname(sys.executable)
else:
    # Якщо .py — беремо каталог на рівень вище, ніж цей файл
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

CREDENTIALS_FILE = os.path.join(base_dir, 'core', 'credentials.json')

SUPABASE_URL = "https://dvjqnzmttscktzbxujex.supabase.co"
DELETE_ACCOUNT_ENDPOINT = f"{SUPABASE_URL}/rest/v1/rpc/delete_account"
CHANGE_PW_ENDPOINT = f"{SUPABASE_URL}/rest/v1/rpc/change_password"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                creds = json.load(f)
                username = creds.get('username', '')
                return username or ''
        except Exception:
            pass
    return '', ''

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(__file__)

def delete_account_rpc(username: str, password: str) -> tuple[bool, str]:
    # викликаєте вашу Supabase RPC “delete_account”
    payload = {
        "input_username": username,
        "input_password": password
    }
    resp = requests.post(DELETE_ACCOUNT_ENDPOINT, json=payload, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        return data.get("status") == "deleted", data.get("message", "")
    return False, f"Server error: {resp.status_code}: {resp.text}"

def change_password_rpc(username: str, old: str, new: str) -> tuple[bool, str]:
    payload = {
        "input_username": username,
        "input_old_password": old,
        "input_new_password": new
    }
    resp = requests.post(CHANGE_PW_ENDPOINT, json=payload, headers=headers)

    if resp.status_code == 200:
        data = resp.json()
        return data.get("status") == "changed", data.get("message", "")
    return False, f"Server error: {resp.status_code}: {resp.text}"
