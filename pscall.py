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
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"last_uid": None}

def save_state(state):
    json.dump(state, open(STATE_FILE, "w"))

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
    """Send message to Telegram"""
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
    r = requests.post(url, json=payload, timeout=15)
    if not r.ok:
        logging.error("Telegram error: %s", r.text)

# ================= CORE LOGIC =================

def fetch_pscall():
    """Fetch latest SMS from PSCall.net"""
    global STATE

    try:
        r = session.get(AJAX_URL, params=build_payload(), timeout=20)
        
        # 🔴 HTML / SESSION EXPIRED CHECK
        if "text/html" in r.headers.get("Content-Type", "").lower():
            logging.warning("⚠️ PSCALL session expired (HTML)")
            return

        try:
            data = r.json()
        except:
            logging.warning("⚠️ Invalid JSON from PSCALL")
            return

        rows = data.get("aaData", [])
        if not rows:
            return

        # Filter valid rows
        valid = []
        for row in rows:
            if (
                isinstance(row, list)
                and len(row) >= 5
                and isinstance(row[0], str)
                and row[0].startswith("20")
            ):
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
        uid = row[0] + row[2] + row[4]

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
        for chat_id in CHAT_IDS:
            send_to_telegram(text, chat_id)
            time.sleep(1)  # Small delay

        # Update state
        STATE["last_uid"] = uid
        save_state(STATE)
        logging.info("LIVE OTP SENT")

    except Exception as e:
        logging.error(f"Error: {e}")

# ================= MAIN =================

def main():
    """Main function"""
    logging.info("🚀 PSCALL.NET BOT STARTED")
    logging.info(f"Bot Token: {'✓' if BOT_TOKEN else '✗'}")
    logging.info(f"Session ID: {'✓' if PHPSESSID else '✗'}")
    logging.info(f"Chat IDs: {CHAT_IDS}")
    
    # Check environment
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN not set!")
        return
    if not PHPSESSID:
        logging.error("PHPSESSID not set!")
        return
    
    # Main loop
    while True:
        try:
            fetch_pscall()
        except Exception as e:
            logging.error(f"Loop error: {e}")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
