import requests
from requests.exceptions import RequestException
import time
import random
import logging
from .config import TOKEN_URL, AUTH_BASE64

HEADERS_BASE = {
    "Authorization": f"Basic {AUTH_BASE64}",
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",
    "WM_SVC.NAME": "Walmart Marketplace",
    #"WM_QOS.CORRELATION_ID": "1234567890"
}

def get_token():    
    while True:
        try:
            resp = requests.post(TOKEN_URL, headers=HEADERS_BASE, data="grant_type=client_credentials", timeout=10)
            if resp.status_code == 200:
                token = resp.json().get("access_token")
                logging.info("OAuth Token received.")
                break
            else:
                logging.warning(f"Token error {resp.status_code}, retrying...")
                time.sleep(5)
        except RequestException as e:
            logging.error(f"Token request failed: {e}")
            time.sleep(5)
    return token

def wait_for_connection():
    logging.info("Network issue detected. Waiting for connection to be restored...")
    print("\nNetwork issue detected. Waiting for connection to be restored...\n")
    time.sleep(10)

def random_sleep(mean=3, std=1):
    delay = random.gauss(mean, std)
    delay = max(0.5, min(delay, 3))
    logging.debug(f"Sleeping for {delay:.2f}s")
    time.sleep(delay)
    return delay

def is_blocked(response):
    if response.status_code == 200:
        if "/blocked?" in str(response.url):
            return True
        if "Robot Check" in response.text or "/blocked?" in response.text.lower():
            return True
    return False

