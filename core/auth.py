import requests
import tkinter as tk
from tkinter import simpledialog, messagebox

AUTH_URL = "http://127.0.0.1:5000/login"

def request_token():
    root = tk.Tk()
    root.withdraw()

    email = simpledialog.askstring("Login", "Enter your email:")
    if email is None:
        return None
    password = simpledialog.askstring("Login", "Enter your password:", show="*")
    if password is None:
        return None

    try:
        response = requests.post(AUTH_URL, json={"email": email, "password": password})
        if response.status_code == 200:
            token = response.json().get("token")
            return token
        else:
            messagebox.showerror("Error", f"Login failed: {response.text}")
    except Exception as e:
        messagebox.showerror("Error", f"Connection error: {str(e)}")

    return None