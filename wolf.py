#!/usr/bin/env python3
import requests
import time
import re
import logging
import json
import os
import random
from datetime import datetime, timedelta
from urllib.parse import urlencode
import html
import threading
from queue import Queue

# ================= CONFIG =================

# Multiple website configurations
WEBSITES = {
    "pscall_net": {
        "name": "PSCall.net",
        "url": "https://pscall.net/client/res/data_smscdr.php",
        "type": "client",
        "columns": 7,
        "referer": "https://pscall.net/client/smscdr.php",
        "date_range": 2  # Days to look back
    },
    "ints_agent": {
        "name": "INTS Agent",
        "url": "http://54.36.173.235/ints/agent/res/data_smscdr.php",
        "type": "agent",
        "columns": 9,
        "referer": "http://54.36.173.235/ints/agent/smscdr.php",
        "date_range": 1
    },
    "ints_client": {
        "name": "INTS Client",
        "url": "http://109.236.84.81/ints/client/res/data_smscdr.php",
        "type": "client",
        "columns": 7,
        "referer": "http://109.236.84.81/ints/client/smscdr.php",
        "date_range": 1
    }
}

# Active website (can be changed via environment variable)
ACTIVE_WEBSITE = os.getenv("ACTIVE_WEBSITE", "pscall_net")

# Bot Configuration - ALL from environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_IDS = os.getenv("CHAT_IDS", "-1003559187782,-1003316982194").split(",")

# Cookies - from environment variable
PHPSESSID = os.getenv("PHPSESSID", "")
COOKIES = {
    "PHPSESSID": PHPSESSID
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

CHECK_INTERVAL = 10  # seconds
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

# Create session for each website
sessions = {}
for site_id, site_config in WEBSITES.items():
    session = requests.Session()
    session.headers.update(HEADERS.copy())
    session.headers["Referer"] = site_config["referer"]
    session.cookies.update(COOKIES)
    sessions[site_id] = session

# ================= STATE =================

def load_state():
    """Load bot state from file"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading state: {e}")
    
    # Initialize state for each website
    state = {}
    for site_id in WEBSITES.keys():
        state[site_id] = {
            "last_uid": None,
            "processed_ids": [],
            "last_check": None
        }
    return state

def save_state(state):
    """Save bot state to file"""
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
    
    # Format: +XXX***XXXX
    country_code = cleaned[:3] if len(cleaned) > 10 else cleaned[:2] if len(cleaned) > 9 else ""
    if country_code:
        main_number = cleaned[len(country_code):]
        if len(main_number) >= 4:
            masked = f"+{country_code}{'*' * (len(main_number) - 4)}{main_number[-4:]}"
            return masked
    
    # Fallback: Show first 3 and last 4
    if len(cleaned) >= 7:
        return f"+{cleaned[:3]}****{cleaned[-4:]}"
    
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

def build_payload(website_config):
    """Build AJAX payload based on website type"""
    today = datetime.now()
    start_date = today - timedelta(days=website_config["date_range"])
    
    fdate1 = start_date.strftime("%Y-%m-%d 00:00:00")
    fdate2 = today.strftime("%Y-%m-%d 23:59:59")
    timestamp = int(time.time() * 1000)
    
    # Common parameters
    params = {
        "fdate1": fdate1,
        "fdate2": fdate2,
        "sEcho": 1,
        "iDisplayStart": 0,
        "iDisplayLength": 25,
        "iSortCol_0": 0,
        "sSortDir_0": "desc",
        "iSortingCols": 1,
        "_": timestamp
    }
    
    # Type-specific parameters
    if website_config["type"] == "agent":
        params.update({
            "frange": "",
            "fclient": "",
            "fnum": "",
            "fcli": "",
            "fgdate": "",
            "fgmonth": "",
            "fgrange": "",
            "fgclient": "",
            "fgnumber": "",
            "fgcli": "",
            "fg": 0,
            "iColumns": 9,
            "sColumns": ",,,,,,,,",
        })
        
        # Add mDataProp parameters for agent
        for i in range(9):
            params[f"mDataProp_{i}"] = i
            params[f"sSearch_{i}"] = ""
            params[f"bRegex_{i}"] = "false"
            params[f"bSearchable_{i}"] = "true"
            params[f"bSortable_{i}"] = "true"
        
        # Last column not sortable
        params["bSortable_8"] = "false"
        
    else:  # client type
        params.update({
            "frange": "",
            "fnum": "",
            "fcli": "",
            "fgdate": "",
            "fgmonth": "",
            "fgrange": "",
            "fgnumber": "",
            "fgcli": "",
            "fg": 0,
            "iColumns": 7,
            "sColumns": ",,,,,,",
        })
        
        # Add mDataProp parameters for client
        for i in range(7):
            params[f"mDataProp_{i}"] = i
            params[f"sSearch_{i}"] = ""
            params[f"bRegex_{i}"] = "false"
            params[f"bSearchable_{i}"] = "true"
            params[f"bSortable_{i}"] = "true"
    
    params["sSearch"] = ""
    params["bRegex"] = "false"
    
    return params

def format_message(row, website_config):
    """Format SMS data into HTML Telegram message"""
    try:
        # Different column structures for different website types
        if website_config["type"] == "agent":
            # Agent: [date, route, number, service, null, message, currency, cost, status]
            date = row[0] if len(row) > 0 else "N/A"
            route = row[1] if len(row) > 1 else "Unknown"
            number = clean_phone_number(row[2]) if len(row) > 2 else "N/A"
            service = row[3] if len(row) > 3 else "Unknown"
            
            # Message might be in column 5
            message = ""
            if len(row) > 5 and row[5]:
                message = row[5]
            elif len(row) > 4 and row[4]:
                message = row[4]
        
        else:  # client type
            # Client: [date, route, number, service, message, currency, cost]
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
                if attempt < retry_count - 1:
                    time.sleep(2)  # Wait before retry
        except Exception as e:
            if attempt < retry_count - 1:
                time.sleep(2)
            else:
                logging.error(f"Error sending to Telegram (chat {chat_id}): {e}")
    
    return False

# ================= CORE LOGIC =================

def fetch_website_sms(site_id, site_config):
    """Fetch latest SMS from specific website"""
    global STATE
    
    if site_id not in STATE:
        STATE[site_id] = {"last_uid": None, "processed_ids": [], "last_check": None}
    
    try:
        session = sessions[site_id]
        params = build_payload(site_config)
        
        logging.debug(f"Fetching data from {site_config['name']} ({site_config['url']})")
        response = session.get(site_config["url"], params=params, timeout=30)
        
        if response.status_code != 200:
            logging.error(f"HTTP Error for {site_config['name']}: {response.status_code}")
            return None
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error for {site_config['name']}: {e}")
            return None
        
        rows = data.get("aaData", [])
        if not rows:
            logging.debug(f"No data found in {site_config['name']} response")
            return None
        
        logging.info(f"{site_config['name']}: Found {len(rows)} total rows")
        
        # Filter valid rows
        valid_rows = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 5:
                continue
            
            # Skip summary rows (different patterns for different sites)
            if isinstance(row[0], str):
                if site_config["type"] == "agent" and row[0].startswith("0,0.01,0,"):
                    continue
                elif row[0].startswith("0,0,0,"):
                    continue
            
            # Check for valid date format
            if not row[0] or not re.match(r'\d{4}-\d{2}-\d{2}', str(row[0])):
                continue
            
            valid_rows.append(row)
        
        logging.info(f"{site_config['name']}: Valid SMS rows: {len(valid_rows)}")
        
        if not valid_rows:
            return None
        
        # Sort by date (newest first)
        valid_rows.sort(
            key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M:%S"),
            reverse=True
        )
        
        return valid_rows[0]  # Return newest row
        
    except requests.RequestException as e:
        logging.error(f"Network error for {site_config['name']}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error for {site_config['name']}: {e}")
    
    return None

def process_sms(newest, site_id, site_config):
    """Process and send SMS"""
    global STATE
    
    # Create unique ID
    sms_id = f"{site_id}_{newest[0]}_{newest[2]}"
    if site_config["type"] == "agent" and len(newest) > 5 and newest[5]:
        sms_id += f"_{hash(str(newest[5])[:50])}"
    elif len(newest) > 4 and newest[4]:
        sms_id += f"_{hash(str(newest[4])[:50])}"
    
    # Check if already processed
    site_state = STATE.get(site_id, {"processed_ids": []})
    if sms_id in site_state.get("processed_ids", []):
        logging.debug(f"No new SMS found in {site_config['name']}")
        return False
    
    logging.info(f"{site_config['name']}: New SMS detected: {newest[2]} at {newest[0]}")
    
    # Format message
    formatted_msg = format_message(newest, site_config)
    if not formatted_msg:
        logging.error(f"Failed to format message from {site_config['name']}")
        return False
    
    # Send to all chat IDs
    success_count = 0
    for chat_id in CHAT_IDS:
        if send_telegram(formatted_msg, chat_id):
            success_count += 1
            time.sleep(0.5)  # Small delay between sends
    
    if success_count > 0:
        logging.info(f"{site_config['name']}: OTP sent to {success_count} chats for {newest[2]}")
        
        # Update state
        if site_id not in STATE:
            STATE[site_id] = {"last_uid": None, "processed_ids": []}
        
        STATE[site_id]["last_uid"] = sms_id
        
        # Keep track of processed IDs
        processed_ids = STATE[site_id].get("processed_ids", [])
        processed_ids.append(sms_id)
        if len(processed_ids) > 200:
            processed_ids = processed_ids[-200:]
        STATE[site_id]["processed_ids"] = processed_ids
        STATE[site_id]["last_check"] = datetime.now().isoformat()
        
        save_state(STATE)
        return True
    else:
        logging.error(f"{site_config['name']}: Failed to send to any chat")
        return False

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ["BOT_TOKEN", "PHPSESSID"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logging.warning(f"Missing environment variables: {', '.join(missing_vars)}")
        logging.warning("Using default values. This may not work properly.")
        return False
    
    return True

def print_config():
    """Print configuration details"""
    logging.info("=" * 60)
    logging.info("🚀 MULTI-SITE OTP BOT STARTED")
    logging.info("=" * 60)
    logging.info(f"Active Website: {WEBSITES[ACTIVE_WEBSITE]['name']}")
    logging.info(f"Chat IDs: {', '.join(CHAT_IDS)}")
    logging.info(f"Check Interval: {CHECK_INTERVAL} seconds")
    logging.info(f"Mask Phone Numbers: {MASK_PHONE}")
    logging.info("=" * 60)
    logging.info("Available Websites:")
    for site_id, config in WEBSITES.items():
        status = "✓ ACTIVE" if site_id == ACTIVE_WEBSITE else "○ INACTIVE"
        logging.info(f"  {status} {config['name']} ({config['type']})")
    logging.info("=" * 60)
    logging.info("Authentication:")
    logging.info(f"Bot Token: {'✓ Set' if os.getenv('BOT_TOKEN') else '✗ Using default'}")
    logging.info(f"Session ID: {'✓ Set' if os.getenv('PHPSESSID') else '✗ Using default'}")
    logging.info("=" * 60)
    logging.info("Button Configuration:")
    logging.info(f"1. 🧑‍💻 Dev: {DEVELOPER_URL}")
    logging.info(f"2. 📱 Numbers 1: {NUMBERS_URL_1}")
    logging.info(f"3. 📱 Numbers 2: {NUMBERS_URL_2}")
    logging.info(f"4. 🆘 Support 1: {SUPPORT_URL_1}")
    logging.info(f"5. 🆘 Support 2: {SUPPORT_URL_2}")
    logging.info("=" * 60)

# ================= MAIN =================

def main():
    """Main function"""
    # Check environment
    if not check_environment():
        logging.warning("Environment check failed. Bot may not work properly.")
    
    print_config()
    
    # Main loop
    error_count = 0
    max_errors = 5
    
    while True:
        try:
            # Fetch from active website
            site_config = WEBSITES[ACTIVE_WEBSITE]
            newest_sms = fetch_website_sms(ACTIVE_WEBSITE, site_config)
            
            if newest_sms:
                process_sms(newest_sms, ACTIVE_WEBSITE, site_config)
            
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

def test_website_connection():
    """Test connection to all websites"""
    logging.info("Testing website connections...")
    
    for site_id, site_config in WEBSITES.items():
        try:
            session = sessions[site_id]
            params = build_payload(site_config)
            
            response = session.get(site_config["url"], params=params, timeout=10)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    rows = len(data.get("aaData", []))
                    logging.info(f"✓ {site_config['name']}: Connected ({rows} rows)")
                except:
                    logging.info(f"✓ {site_config['name']}: Connected (non-JSON response)")
            else:
                logging.error(f"✗ {site_config['name']}: HTTP {response.status_code}")
                
        except Exception as e:
            logging.error(f"✗ {site_config['name']}: {str(e)}")

if __name__ == "__main__":
    # Test connections first
    test_website_connection()
    
    # Run main bot
    main()
