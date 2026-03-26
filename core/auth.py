import requests
import os
import json
import logging
import sys

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

CREDENTIALS_FILE = os.path.join(base_dir, 'core', 'credentials.json')

SUPABASE_URL = "https://dvjqnzmttscktzbxujex.supabase.co"
DELETE_ACCOUNT_ENDPOINT = f"{SUPABASE_URL}/rest/v1/rpc/delete_account"
CHANGE_PW_ENDPOINT = f"{SUPABASE_URL}/rest/v1/rpc/change_password"


def _get_supabase_headers() -> dict:
    # Будуємо headers при кожному виклику, щоб не залежати від порядку імпорту
    key = os.environ.get("SUPABASE_KEY", "")
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }


def load_credentials() -> str:
    """Returns saved username as string, or empty string if not found."""
    if os.path.exists(CREDENTIALS_FILE):
        try:
            with open(CREDENTIALS_FILE, 'r', encoding='utf-8') as f:
                creds = json.load(f)
                return creds.get('username', '') or ''
        except Exception as e:
            logging.debug("Could not load credentials from file: %s", e)
    return ''


def delete_account_rpc(username: str, password: str) -> tuple[bool, str]:
    payload = {"input_username": username, "input_password": password}
    resp = requests.post(DELETE_ACCOUNT_ENDPOINT, json=payload, headers=_get_supabase_headers())
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
    resp = requests.post(CHANGE_PW_ENDPOINT, json=payload, headers=_get_supabase_headers())
    if resp.status_code == 200:
        data = resp.json()
        return data.get("status") == "changed", data.get("message", "")
    return False, f"Server error: {resp.status_code}: {resp.text}"
