#!/usr/bin/env python3
import requests
import time
import re
import logging
import json
import os
from datetime import datetime

# ================= ENV =================

AJAX_URL = os.getenv("AJAX_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PHPSESSID = os.getenv("PHPSESSID")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "10"))
SUPPORT_URL = os.getenv("SUPPORT_URL")
NUMBERS_URL = os.getenv("NUMBERS_URL")

if not all([AJAX_URL, BOT_TOKEN, CHAT_ID, PHPSESSID]):
    raise RuntimeError("Missing required ENV variables")

# ================= CONFIG =================

COOKIES = {
    "PHPSESSID": PHPSESSID
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01"
}

STATE_FILE = "state.json"

# ================= LOGGING =================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(COOKIES)

# ================= STATE =================

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            return json.load(open(STATE_FILE))
        except:
            pass
    return {"last_uid": None}

def save_state(state):
    json.dump(state, open(STATE_FILE, "w"))

STATE = load_state()

# ================= HELPERS =================

def extract_otp(text):
    if not text:
        return "N/A"
    m = re.search(r"\b(\d{4,8})\b", text)
    return m.group(1) if m else "N/A"

def build_payload():
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
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
        "sEcho": 1,
        "iColumns": 9,
        "iDisplayStart": 0,
        "iDisplayLength": 25,
        "iSortCol_0": 0,
        "sSortDir_0": "desc",
        "iSortingCols": 1
    }

def format_message(row):
    date = row[0]
    route_raw = row[1] or "Unknown"
    number = row[2] or "N/A"
    service = row[3] or "Unknown"
    message = row[5] or ""

    country = route_raw.split("-")[0]

    if not number.startswith("+"):
        number = "+" + number

    otp = extract_otp(message)

    return (
        "📩 *LIVE OTP RECEIVED*\n\n"
        f"📞 *Number:* `{number}`\n"
        f"🔢 *OTP:* 🔥 `{otp}` 🔥\n"
        f"🏷 *Service:* {service}\n"
        f"🌍 *Country:* {country}\n"
        f"🕒 *Time:* {date}\n\n"
        f"💬 *SMS:*\n{message}\n\n"
        "⚡ *CYBER CORE OTP*"
    )

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "🆘 Support", "url": SUPPORT_URL},
                    {"text": "📲 Numbers", "url": NUMBERS_URL}
                ]
            ]
        }
    }
    requests.post(url, json=payload, timeout=15)

# ================= CORE (ONLY LIVE) =================

def fetch_latest_sms():
    global STATE

    r = session.get(AJAX_URL, params=build_payload(), timeout=20)
    data = r.json()

    rows = data.get("aaData", [])
    if not rows:
        return

    valid = [
        r for r in rows
        if isinstance(r, list)
        and isinstance(r[0], str)
        and re.match(r"\d{4}-\d{2}-\d{2}", r[0])
    ]

    if not valid:
        return

    valid.sort(
        key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M:%S"),
        reverse=True
    )

    newest = valid[0]
    uid = newest[0] + newest[2] + (newest[5] or "")

    if STATE["last_uid"] is None:
        STATE["last_uid"] = uid
        save_state(STATE)
        logging.info("LIVE baseline set")
        return

    if uid != STATE["last_uid"]:
        STATE["last_uid"] = uid
        save_state(STATE)
        send_telegram(format_message(newest))
        logging.info("LIVE OTP SENT")

# ================= LOOP =================

logging.info("🚀 INTS SMS BOT STARTED (ONLY LIVE MODE)")

while True:
    try:
        fetch_latest_sms()
    except Exception:
        logging.exception("ERROR")
    time.sleep(CHECK_INTERVAL)
