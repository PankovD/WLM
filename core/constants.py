import os, sys

APP_NAME = "Walmart Parser"

if getattr(sys, 'frozen', False):
    # Якщо .exe — беремо директорію з .exe (onedir launcher.exe)
    base_dir = os.path.dirname(sys.executable)
else:
    # Якщо .py — беремо каталог на рівень вище, ніж цей файл
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

COLUMNS_FILE = os.path.join(base_dir,    'core', 'config','columns.json')
CONFIGURED_FILE = os.path.join(base_dir, 'core', 'config','configured_columns.json')
DEFAULT_FILE = os.path.join(base_dir,    'core', 'config','default_columns.json')

RESULT_HEADER = [
    'Store Page', 'Catalog Page', 'Product Title', 'Product ID',
    'Selling Price', 'Active Sellers', 'Ratings', 'Average Rating',
    'Current Seller', 'UPC', 'PRICE'
]


# HTTP headers для парсингу сторінок
BASE_HEADERS = [
    {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,uk;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "referer": "https://www.walmart.com/",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "connection": "keep-alive",
    "cache-control": "max-age=0",
    "viewport-width": "1920",
    "device-memory": "8",
    "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="123", "Google Chrome";v="123"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"10.0.0"',
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    #"cookie": "consent=yes;"
    },

    {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,uk;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "referer": "https://www.walmart.com/",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "connection": "keep-alive",
    "cache-control": "max-age=0",
    "viewport-width": "1920",
    "device-memory": "8",
    "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="123", "Google Chrome";v="123"',
    #"sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"10.0.0"',
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    #"cookie": "consent=yes;"    
    },

    {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,uk;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "referer": "https://www.walmart.com/",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "connection": "keep-alive",
    "cache-control": "max-age=0",
    "viewport-width": "1920",
    "device-memory": "8",
    "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="123", "Google Chrome";v="123"',
    #"sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"10.0.0"',
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    "cookie": "consent=yes;"    
    },
    
    {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,uk;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "referer": "https://www.walmart.com/",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "connection": "keep-alive",
    "cache-control": "max-age=0",
    "viewport-width": "1485",
    "device-memory": "4",
    "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"123\", \"Google Chrome\";v=\"123\"",
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua-platform-version": "\"10.0.0\"",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    "cookie": "consent=yes;"
    },
    
    {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,uk;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "referer": "https://www.walmart.com/",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "connection": "keep-alive",
    "cache-control": "max-age=0",
    "viewport-width": "1871",
    "device-memory": "16",
    "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"123\", \"Google Chrome\";v=\"123\"",
    # sec-ch-ua-mobile видалено
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua-platform-version": "\"10.0.0\"",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document"
    # cookie видалено
    },
    
    {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,uk;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "referer": "https://www.walmart.com/",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "connection": "keep-alive",
    "cache-control": "max-age=0",
    "viewport-width": "1866",
    "device-memory": "8",
    "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"123\", \"Google Chrome\";v=\"123\"",
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua-platform-version": "\"10.0.0\"",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document"
    # cookie не вказано
    },
    
    {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9,uk;q=0.8",
    "accept-encoding": "gzip, deflate, br",
    "referer": "https://www.walmart.com/",
    "upgrade-insecure-requests": "1",
    "dnt": "1",
    "connection": "keep-alive",
    "cache-control": "max-age=0",
    "viewport-width": "1574",
    "device-memory": "16",
    "sec-ch-ua": "\"Not.A/Brand\";v=\"8\", \"Chromium\";v=\"123\", \"Google Chrome\";v=\"123\"",
    # sec-ch-ua-mobile видалено
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-ch-ua-platform-version": "\"10.0.0\"",
    "sec-fetch-site": "same-origin",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    "cookie": "consent=yes;"
    }
]
