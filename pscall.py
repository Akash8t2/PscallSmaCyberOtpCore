#!/usr/bin/env python3
import requests
import time
import re
import logging
import json
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode
import html

# ================= CONFIG =================

# Website configuration for PSCall.net (CLIENT interface)
AJAX_URL = "https://pscall.net/client/res/data_smscdr.php"
REFERER_URL = "https://pscall.net/client/smscdr.php"

# Bot Configuration - ALL from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_IDS = os.getenv("CHAT_IDS", "-1003559187782,-1003316982194").split(",")

# Cookies - from environment variable (PSCall.net session)
PHPSESSID = os.getenv("PHPSESSID", "")
COOKIES = {
    "PHPSESSID": PHPSESSID
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Referer": REFERER_URL,
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "DNT": "1",
    "Sec-GPC": "1"
}

CHECK_INTERVAL = 15  # Check every 15 seconds
STATE_FILE = "state.json"

# Button URLs - ALL from environment variables
DEVELOPER_URL = "https://t.me/botcasx"
NUMBERS_URL_1 = os.getenv("NUMBERS_URL_1", "https://t.me/alltgmethod11")
NUMBERS_URL_2 = os.getenv("NUMBERS_URL_2", "https://t.me/CyberOTPCore")
SUPPORT_URL_1 = os.getenv("SUPPORT_URL_1", "https://t.me/+zu_E8bhN0WU5OTNl")
SUPPORT_URL_2 = os.getenv("SUPPORT_URL_2", "https://t.me/CYBER_OTP1_CORE")

# Mask phone number settings
MASK_PHONE = os.getenv("MASK_PHONE", "true").lower() == "true"

# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

# Suppress urllib3 warnings
logging.getLogger("urllib3").setLevel(logging.WARNING)

# Create session
session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(COOKIES)

# ================= STATE =================

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading state: {e}")
    return {"last_uid": None, "processed_ids": []}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving state: {e}")

STATE = load_state()

# ================= HELPERS =================

def mask_phone_number(number):
    """Mask phone number showing only first 3 and last 4 digits"""
    if not number or number == "N/A":
        return "N/A"
    
    # Remove all non-digit characters
    cleaned = re.sub(r'\D', '', number)
    
    if len(cleaned) < 7:
        return cleaned  # Too short to mask
    
    # For Somalia numbers like 252652015847
    # Format: 252***5847 (show country code + last 4 digits)
    if cleaned.startswith("252") and len(cleaned) > 6:
        # Keep first 3 digits (country code) and last 4 digits
        return f"{cleaned[:3]}***{cleaned[-4:]}"
    
    # For other numbers, show first 3 and last 4 digits
    if len(cleaned) >= 7:
        return f"{cleaned[:3]}***{cleaned[-4:]}"
    
    return cleaned

def extract_otp(text):
    """Extract OTP from SMS text"""
    if not text:
        return "N/A"
    
    # Telegram codes
    telegram_match = re.search(r'Telegram code\s+(\d{4,8})', text)
    if telegram_match:
        return telegram_match.group(1)
    
    # WhatsApp codes
    whatsapp_match = re.search(r'WhatsApp code\s+(\d{4,8})', text)
    if whatsapp_match:
        return whatsapp_match.group(1)
    
    # General patterns
    patterns = [
        r'\b(\d{4,8})\b',
        r'code[\s:]+(\d{4,8})',
        r'OTP[\s:]+(\d{4,8})',
        r'verification[\s:]+(\d{4,8})',
        r'密码[\s:]+(\d{4,8})',
        r'코드[\s:]+(\d{4,8})',
        r'код[\s:]+(\d{4,8})',
        r'कूट[\s:]+(\d{4,8})',  # Hindi
        r'كود[\s:]+(\d{4,8})',  # Arabic
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "N/A"

def clean_phone_number(number):
    """Clean and format phone number"""
    if not number:
        return "N/A"
    
    cleaned = re.sub(r'\D', '', number)
    if len(cleaned) >= 10:
        return f"+{cleaned}"
    return number

def build_payload():
    """Build AJAX payload for PSCall.net CLIENT interface (7 columns)"""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    fdate1 = yesterday.strftime("%Y-%m-%d 00:00:00")
    fdate2 = today.strftime("%Y-%m-%d 23:59:59")
    timestamp = int(time.time() * 1000)
    
    params = {
        "fdate1": fdate1,
        "fdate2": fdate2,
        "frange": "",
        "fnum": "",
        "fcli": "",
        "fgdate": "",
        "fgmonth": "",
        "fgrange": "",
        "fgnumber": "",
        "fgcli": "",
        "fg": 0,
        "sEcho": 1,
        "iColumns": 7,  # 7 columns for client interface
        "sColumns": ",,,,,,",  # 6 commas for 7 columns
        "iDisplayStart": 0,
        "iDisplayLength": 25,
        "mDataProp_0": 0,
        "sSearch_0": "",
        "bRegex_0": "false",
        "bSearchable_0": "true",
        "bSortable_0": "true",
        "mDataProp_1": 1,
        "sSearch_1": "",
        "bRegex_1": "false",
        "bSearchable_1": "true",
        "bSortable_1": "true",
        "mDataProp_2": 2,
        "sSearch_2": "",
        "bRegex_2": "false",
        "bSearchable_2": "true",
        "bSortable_2": "true",
        "mDataProp_3": 3,
        "sSearch_3": "",
        "bRegex_3": "false",
        "bSearchable_3": "true",
        "bSortable_3": "true",
        "mDataProp_4": 4,
        "sSearch_4": "",
        "bRegex_4": "false",
        "bSearchable_4": "true",
        "bSortable_4": "true",
        "mDataProp_5": 5,
        "sSearch_5": "",
        "bRegex_5": "false",
        "bSearchable_5": "true",
        "bSortable_5": "true",
        "mDataProp_6": 6,
        "sSearch_6": "",
        "bRegex_6": "false",
        "bSearchable_6": "true",
        "bSortable_6": "true",
        "sSearch": "",
        "bRegex": "false",
        "iSortCol_0": 0,
        "sSortDir_0": "desc",
        "iSortingCols": 1,
        "_": timestamp
    }
    
    return params

def format_message(row):
    """Format SMS data into HTML Telegram message for PSCall.net CLIENT interface (7 columns)"""
    try:
        # PSCall.net CLIENT interface has 7 columns
        # Based on sample: [date, route, number, service, message, currency, cost]
        date = row[0] if len(row) > 0 else "N/A"
        route = row[1] if len(row) > 1 else "Unknown"
        number = clean_phone_number(row[2]) if len(row) > 2 else "N/A"
        service = row[3] if len(row) > 3 else "Unknown"
        message = row[4] if len(row) > 4 else ""
        
        # Extract country from route
        country = "Unknown"
        if route and isinstance(route, str):
            # Remove any numbers/dashes and take first word
            country_parts = re.split(r'[\d-]', route, 1)
            if country_parts and country_parts[0].strip():
                country = country_parts[0].strip()
        
        # Extract OTP
        otp = extract_otp(message)
        
        # Mask phone number if enabled
        if MASK_PHONE:
            display_number = mask_phone_number(number)
        else:
            display_number = number
        
        # Escape HTML special characters
        safe_number = html.escape(str(display_number))
        safe_otp = html.escape(str(otp))
        safe_service = html.escape(str(service))
        safe_country = html.escape(str(country))
        safe_date = html.escape(str(date))
        
        # Format message
        safe_message = html.escape(str(message))
        
        # Format as HTML with newlines
        formatted = (
            "💎 <b>PREMIUM OTP ALERT</b> 💎\n"
            "<i>Instant • Secure • Verified</i>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"📞 <b>Number</b> <code>{safe_number}</code>\n"
            f"🔐 <b>OTP CODE</b> 🔥 <code>{safe_otp}</code> 🔥\n"
            f"🏷 <b>Service</b> <b>{safe_service}</b>\n"
            f"🌍 <b>Country</b> <b>{safe_country}</b>\n"
            f"🕒 <b>Received At</b> <code>{safe_date}</code>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"💬 <b>Message Content</b>\n"
            f"<i>{safe_message}</i>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "⚡ <b>POWERED BY @Rohit512R</b>"
        )
        
        return formatted
    except Exception as e:
        logging.error(f"Error formatting message: {e}")
        return None

def create_keyboard():
    """Create inline keyboard with 5 buttons"""
    return {
        "inline_keyboard": [
            # First row: 3 buttons
            [
                {"text": "🧑‍💻 Dev", "url": DEVELOPER_URL},
                {"text": "📱 Numbers 1", "url": NUMBERS_URL_1},
                {"text": "📱 Numbers 2", "url": NUMBERS_URL_2}
            ],
            # Second row: 2 buttons
            [
                {"text": "🆘 Support 1", "url": SUPPORT_URL_1},
                {"text": "🆘 Support 2", "url": SUPPORT_URL_2}
            ]
        ]
    }

def send_telegram(text, chat_id, retry_count=3):
    """Send message to specific Telegram chat with retry"""
    if not text:
        return False
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": create_keyboard()
    }
    
    for attempt in range(retry_count):
        try:
            response = requests.post(url, json=payload, timeout=15)
            if response.status_code == 200:
                return True
            else:
                error_data = response.json()
                logging.error(f"Telegram API error (attempt {attempt+1}/{retry_count}): {error_data.get('description', 'Unknown error')}")
                if attempt < retry_count - 1:
                    time.sleep(2)  # Wait before retry
        except Exception as e:
            logging.error(f"Error sending to Telegram (attempt {attempt+1}/{retry_count}): {e}")
            if attempt < retry_count - 1:
                time.sleep(2)
    
    return False

# ================= CORE LOGIC =================

def check_session_valid():
    """Check if the session is still valid by making a test request"""
    try:
        # Try to access the main page first
        test_response = session.get(REFERER_URL, timeout=10)
        
        if test_response.status_code != 200:
            logging.error(f"Session check failed: HTTP {test_response.status_code}")
            return False
        
        # Check if we're redirected to login page
        if "login" in test_response.url.lower() or "index.php" in test_response.url.lower():
            logging.error("Session expired: Redirected to login page")
            return False
        
        return True
    except Exception as e:
        logging.error(f"Session check error: {e}")
        return False

def fetch_latest_sms():
    """Fetch latest SMS from PSCall.net website"""
    global STATE
    
    try:
        # First check if session is valid
        if not check_session_valid():
            logging.error("Session invalid. Please update PHPSESSID in environment variables.")
            return
        
        params = build_payload()
        
        logging.info(f"Fetching data from PSCall.net")
        response = session.get(AJAX_URL, params=params, timeout=30)
        
        if response.status_code != 200:
            logging.error(f"HTTP Error: {response.status_code}")
            logging.debug(f"Response text: {response.text[:500]}")
            return
        
        # Log response headers for debugging
        logging.debug(f"Response Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        logging.debug(f"Response Length: {len(response.text)}")
        
        # Check if response is HTML (login page)
        if 'text/html' in response.headers.get('Content-Type', '').lower():
            logging.error("Received HTML response instead of JSON. Session may be expired.")
            logging.debug(f"HTML response start: {response.text[:200]}")
            return
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            logging.debug(f"Raw response (first 500 chars): {response.text[:500]}")
            return
        
        rows = data.get("aaData", [])
        if not rows:
            logging.debug("No data found in response")
            return
        
        logging.info(f"Found {len(rows)} total rows")
        
        # Filter valid rows
        valid_rows = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 5:
                continue
            
            # Skip summary rows (they start with "0,0.01,0," for PSCall.net)
            if isinstance(row[0], str) and row[0].startswith("0,0.01,0,"):
                continue
            
            # Check for valid date format
            if not row[0] or not re.match(r'\d{4}-\d{2}-\d{2}', str(row[0])):
                continue
            
            valid_rows.append(row)
        
        logging.info(f"Valid SMS rows: {len(valid_rows)}")
        
        if not valid_rows:
            return
        
        # Sort by date (newest first)
        valid_rows.sort(
            key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M:%S"),
            reverse=True
        )
        
        # Process newest row
        newest = valid_rows[0]
        
        # Create unique ID
        sms_id = f"{newest[0]}_{newest[2]}"
        if len(newest) > 4 and newest[4]:
            sms_id += f"_{hash(str(newest[4])[:50])}"
        
        # Check if already processed
        if STATE["last_uid"] == sms_id or sms_id in STATE.get("processed_ids", []):
            logging.debug("No new SMS found")
            return
        
        logging.info(f"New SMS detected: {newest[2]} at {newest[0]}")
        
        # Format message
        formatted_msg = format_message(newest)
        if not formatted_msg:
            logging.error("Failed to format message")
            return
        
        # Send to all chat IDs
        success_count = 0
        for chat_id in CHAT_IDS:
            if send_telegram(formatted_msg, chat_id):
                success_count += 1
                time.sleep(1)  # Small delay between sends
        
        if success_count > 0:
            logging.info(f"OTP sent to {success_count} chats for {newest[2]}")
            
            # Update state
            STATE["last_uid"] = sms_id
            
            # Keep track of processed IDs
            processed_ids = STATE.get("processed_ids", [])
            processed_ids.append(sms_id)
            if len(processed_ids) > 200:
                processed_ids = processed_ids[-200:]
            STATE["processed_ids"] = processed_ids
            
            save_state(STATE)
        else:
            logging.error("Failed to send to any chat")
        
    except requests.RequestException as e:
        logging.error(f"Network error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ["BOT_TOKEN", "PHPSESSID"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logging.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logging.warning("Bot will not work without these variables.")
        return False
    
    return True

def print_config():
    """Print configuration details"""
    logging.info("=" * 60)
    logging.info("🚀 PSCall.net OTP BOT STARTED")
    logging.info("=" * 60)
    logging.info(f"Website: PSCall.net (Client Interface)")
    logging.info(f"URL: {AJAX_URL}")
    logging.info(f"Chat IDs: {', '.join(CHAT_IDS)}")
    logging.info(f"Check Interval: {CHECK_INTERVAL} seconds")
    logging.info(f"Mask Phone Numbers: {MASK_PHONE}")
    logging.info("=" * 60)
    logging.info("Authentication:")
    logging.info(f"Bot Token: {'✓ Set' if os.getenv('BOT_TOKEN') else '✗ NOT SET'}")
    logging.info(f"Session ID: {'✓ Set' if os.getenv('PHPSESSID') else '✗ NOT SET'}")
    logging.info("=" * 60)
    logging.info("Button Configuration:")
    logging.info(f"1. 🧑‍💻 Dev: {DEVELOPER_URL}")
    logging.info(f"2. 📱 Numbers 1: {NUMBERS_URL_1}")
    logging.info(f"3. 📱 Numbers 2: {NUMBERS_URL_2}")
    logging.info(f"4. 🆘 Support 1: {SUPPORT_URL_1}")
    logging.info(f"5. 🆘 Support 2: {SUPPORT_URL_2}")
    logging.info("=" * 60)

def test_connection():
    """Test connection to PSCall.net"""
    logging.info("Testing connection to PSCall.net...")
    
    try:
        # First test session
        if check_session_valid():
            logging.info("✓ Session is valid")
        else:
            logging.error("✗ Session is invalid. Please update PHPSESSID.")
            return False
        
        # Test API call
        params = build_payload()
        response = session.get(AJAX_URL, params=params, timeout=15)
        
        if response.status_code == 200:
            try:
                data = response.json()
                rows = len(data.get("aaData", []))
                logging.info(f"✓ API connection successful ({rows} rows found)")
                return True
            except json.JSONDecodeError:
                logging.error("✗ API returned non-JSON response")
                return False
        else:
            logging.error(f"✗ API connection failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        logging.error(f"✗ Connection test failed: {e}")
        return False

# ================= MAIN =================

def main():
    """Main function"""
    # Check environment
    if not check_environment():
        logging.error("Critical environment variables missing. Exiting.")
        return
    
    print_config()
    
    # Test connection
    if not test_connection():
        logging.error("Connection test failed. Please check your configuration.")
        logging.error("1. Make sure PHPSESSID is correct")
        logging.error("2. Make sure you're logged into PSCall.net")
        logging.error("3. Check if the website is accessible")
        return
    
    # Main loop
    error_count = 0
    max_errors = 10
    
    while True:
        try:
            fetch_latest_sms()
            error_count = 0  # Reset error count on success
            
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
            break
        except Exception as e:
            error_count += 1
            logging.error(f"Error in main loop ({error_count}/{max_errors}): {e}")
            
            if error_count >= max_errors:
                logging.error("Too many consecutive errors. Waiting 60 seconds...")
                time.sleep(60)
                error_count = 0
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
