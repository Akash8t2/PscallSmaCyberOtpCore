#!/usr/bin/env python3
import requests
import time
import re
import logging
import json
import os
from datetime import datetime
from urllib.parse import urlencode
import html

# ================= CONFIG =================

AJAX_URL = "https://pscall.net/client/res/data_smscdr.php"

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_IDS = os.getenv("CHAT_IDS", "-1003559187782,-1003316982194").split(",")

# Cookies
PHPSESSID = os.getenv("PHPSESSID", "")
COOKIES = {
    "PHPSESSID": PHPSESSID
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://pscall.net/client/SMSCDRReports"
}

CHECK_INTERVAL = 10
STATE_FILE = "state.json"

# Button URLs
DEVELOPER_URL = "https://t.me/botcasx"
NUMBERS_URL_1 = os.getenv("NUMBERS_URL_1", "https://t.me/alltgmethod11")
NUMBERS_URL_2 = os.getenv("NUMBERS_URL_2", "https://t.me/CyberOTPCore")
SUPPORT_URL_1 = os.getenv("SUPPORT_URL_1", "https://t.me/+zu_E8bhN0WU5OTNl")
SUPPORT_URL_2 = os.getenv("SUPPORT_URL_2", "https://t.me/CYBER_OTP1_CORE")

# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(COOKIES)

# ================= STATE =================

def load_state():
    """Safely load state from file"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading state: {e}")
    return {"last_uid": None}

def save_state(state):
    """Safely save state to file (NO FILE CORRUPTION)"""
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        logging.error(f"Error saving state: {e}")

STATE = load_state()

# ================= HELPERS =================

def mask_number(number: str) -> str:
    """Mask phone number showing first 3 and last 4 digits"""
    if not number or len(number) < 8:
        return number
    return number[:3] + "*" * (len(number) - 7) + number[-4:]

def extract_otp(text: str) -> str:
    """Extract OTP from SMS text"""
    if not text:
        return "N/A"
    m = re.search(r"\b(\d{4,8})\b", text)
    return m.group(1) if m else "N/A"

def build_payload():
    """Build payload for PSCall.net"""
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
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
        "iColumns": 7,
        "sColumns": ",,,,,,",
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
        "_": int(time.time() * 1000)
    }

def send_to_telegram(text, chat_id):
    """Send message to Telegram with proper error logging"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "🧑‍💻 Dev", "url": DEVELOPER_URL},
                    {"text": "📱 Numbers 1", "url": NUMBERS_URL_1},
                    {"text": "📱 Numbers 2", "url": NUMBERS_URL_2}
                ],
                [
                    {"text": "🆘 Support 1", "url": SUPPORT_URL_1},
                    {"text": "🆘 Support 2", "url": SUPPORT_URL_2}
                ]
            ]
        }
    }
    
    try:
        r = requests.post(url, json=payload, timeout=15)
        if not r.ok:
            # 🔧 Fix 3: Telegram error visibility (DEBUG HELP)
            logging.error(f"Telegram error | chat={chat_id} | status={r.status_code} | {r.text[:100]}")
            return False
        return True
    except Exception as e:
        logging.error(f"Telegram connection error | chat={chat_id} | {e}")
        return False

# ================= CORE LOGIC =================

def fetch_pscall():
    """Fetch latest SMS from PSCall.net"""
    global STATE

    try:
        r = session.get(AJAX_URL, params=build_payload(), timeout=20)
        
        # 🔧 Fix 4: HTML login page stronger detect
        content_type = r.headers.get("Content-Type", "").lower()
        response_text = r.text.lower()
        
        # Check if response is HTML (login page)
        if "text/html" in content_type or "<!doctype html" in response_text or "<html" in response_text:
            logging.warning("⚠️ PSCALL session expired - HTML login page detected")
            return
        
        # Check if response is empty or too small
        if len(r.text.strip()) < 10:
            logging.warning("⚠️ Empty response from PSCALL")
            return
        
        try:
            data = r.json()
        except json.JSONDecodeError as e:
            logging.warning(f"⚠️ Invalid JSON from PSCALL: {e}")
            logging.debug(f"Response preview: {r.text[:200]}")
            return

        rows = data.get("aaData", [])
        if not rows:
            return

        # 🔧 Fix 1: Dummy row + date validation (VERY IMPORTANT)
        valid = []
        for row in rows:
            if not isinstance(row, list):
                continue
            if len(row) < 5:
                continue
            if not isinstance(row[0], str):
                continue
            
            # Skip dummy/summary rows (like "0,0.01,0,9")
            if row[0].startswith("0,") or "," in row[0]:
                continue
            
            # Strict datetime check
            try:
                datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            
            valid.append(row)

        if not valid:
            return

        # Sort by date (newest first)
        valid.sort(
            key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M:%S"),
            reverse=True
        )

        # Get newest row
        row = valid[0]
        
        # Create unique ID
        uid = f"{row[0]}_{row[2]}_{hash(str(row[4])[:50])}"

        # Check if already processed
        if STATE["last_uid"] == uid:
            return

        # Extract data
        date = row[0]
        route = row[1]
        number_raw = row[2]
        service = row[3]
        message = row[4]

        # Extract OTP
        otp = extract_otp(message)
        if otp == "N/A":
            logging.debug(f"No OTP found in message: {message[:50]}...")
            return

        # Mask phone number
        masked_number = mask_number(number_raw)

        # Format message
        text = f"""📩 <b>LIVE OTP RECEIVED</b>

📞 <b>Number:</b> <code>{masked_number}</code>
🔢 <b>OTP:</b> 🔥 <code>{otp}</code> 🔥
🏷 <b>Service:</b> {service}
🌍 <b>Route:</b> {route}
🕒 <b>Time:</b> {date}

💬 <b>SMS:</b>
{html.escape(message)}

⚡ <b>POWERED BY @Rohit512R</b>
"""

        # Send to all chats
        success_count = 0
        for chat_id in CHAT_IDS:
            if send_to_telegram(text, chat_id):
                success_count += 1
                time.sleep(1)  # Small delay between sends

        if success_count > 0:
            # Update state
            STATE["last_uid"] = uid
            save_state(STATE)
            logging.info(f"✅ LIVE OTP SENT to {success_count} chats | OTP: {otp} | Number: {masked_number}")
        else:
            logging.error("❌ Failed to send OTP to any chat")

    except requests.RequestException as e:
        logging.error(f"Network error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in fetch_pscall: {e}")
        import traceback
        traceback.print_exc()

# ================= MAIN =================

def main():
    """Main function"""
    logging.info("=" * 60)
    logging.info("🚀 PSCALL.NET BOT STARTED (PRODUCTION READY)")
    logging.info("=" * 60)
    
    # Check environment
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN not set in environment variables!")
        logging.error("Set with: heroku config:set BOT_TOKEN=your_token")
        return
    
    if not PHPSESSID:
        logging.error("❌ PHPSESSID not set in environment variables!")
        logging.error("Set with: heroku config:set PHPSESSID=your_session_id")
        logging.error("Get session ID from browser after logging into PSCall.net")
        return
    
    logging.info(f"✅ Bot Token: {'Set' if BOT_TOKEN else 'Not Set'}")
    logging.info(f"✅ Session ID: {'Set' if PHPSESSID else 'Not Set'}")
    logging.info(f"✅ Chat IDs: {CHAT_IDS}")
    logging.info(f"✅ Check Interval: {CHECK_INTERVAL} seconds")
    logging.info("=" * 60)
    logging.info("Features:")
    logging.info("  ✅ Phone number masking (e.g., 252***5847)")
    logging.info("  ✅ Dummy row filtering")
    logging.info("  ✅ Session expiry detection")
    logging.info("  ✅ State persistence")
    logging.info("  ✅ 5-button Telegram interface")
    logging.info("  ✅ Powered by @Rohit512R")
    logging.info("=" * 60)
    
    # Test session on startup
    try:
        logging.info("Testing PSCall.net connection...")
        test_params = build_payload()
        test_params["iDisplayLength"] = 5  # Small test
        response = session.get(AJAX_URL, params=test_params, timeout=10)
        
        if response.status_code == 200:
            try:
                data = response.json()
                row_count = len(data.get("aaData", []))
                logging.info(f"✅ Connection successful | Found {row_count} rows")
            except:
                logging.warning("⚠️ Got response but not valid JSON")
        else:
            logging.error(f"❌ Connection failed | HTTP {response.status_code}")
    except Exception as e:
        logging.error(f"❌ Connection test error: {e}")
    
    # Main loop
    logging.info("Starting main monitoring loop...")
    logging.info("=" * 60)
    
    error_count = 0
    max_errors = 5
    
    while True:
        try:
            fetch_pscall()
            error_count = 0  # Reset error count on success
            
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
            break
        except Exception as e:
            error_count += 1
            logging.error(f"Main loop error ({error_count}/{max_errors}): {e}")
            
            if error_count >= max_errors:
                logging.error("Too many errors. Waiting 60 seconds...")
                time.sleep(60)
                error_count = 0
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
