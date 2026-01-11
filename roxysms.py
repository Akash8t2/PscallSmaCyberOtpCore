#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NumberPanel OTP Bot
Mode: LAST 3 OTP ONLY
sesskey + PHPSESSID FIXED
Heroku / VPS Compatible
"""

import time
import json
import re
import requests
from datetime import datetime

# ================= CONFIG =================
API_URL = "http://51.89.99.105/NumberPanel/client/res/data_smscdr.php"

# 🔐 NEW VALUES (as provided by you)
PHPSESSID = "oktoq8i2e1ebb5mjtp5nkumprd"
SESSKEY   = "Q05RR0FPT0pBVQ=="

BOT_TOKEN = "PASTE_YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID   = "-1003405109562"

CHECK_INTERVAL = 12
STATE_FILE = "state.json"

# ================= HEADERS =================
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "http://51.89.99.105/NumberPanel/client/SMSDashboard",
    "Accept-Encoding": "identity",
    "Connection": "close",
}

# ================= HELPERS =================
def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {"sent": []}

def save_state(data):
    json.dump(data, open(STATE_FILE, "w"))

def extract_otp(text):
    """
    Supports:
    123456
    589-837
    589 837
    """
    if not text:
        return None
    m = re.search(r"\b(\d{3,4}[-\s]?\d{3,4})\b", text)
    return m.group(1) if m else None

def send_telegram(msg):
    r = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        },
        timeout=10
    )
    print("📤 Telegram:", r.status_code)

# ================= START =================
print("🚀 NumberPanel OTP Bot Started")
print("⚡ Mode: LAST 3 OTP ONLY")
print("📢 Group:", CHAT_ID)

state = load_state()
sent = state["sent"]

while True:
    try:
        cookies = {
            "PHPSESSID": PHPSESSID
        }

        params = {
            "sesskey": SESSKEY,                    # 🔥 REQUIRED
            "fdate1": "2026-01-09 00:00:00",
            "fdate2": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "iDisplayStart": 0,
            "iDisplayLength": 3,                  # 🔥 LAST 3 ONLY
            "sEcho": 1,
            "_": int(time.time() * 1000),
        }

        r = requests.get(
            API_URL,
            headers=HEADERS,
            cookies=cookies,
            params=params,
            timeout=15
        )

        if not r.text or not r.text.strip():
            print("⚠️ Empty response")
            time.sleep(CHECK_INTERVAL)
            continue

        if "login" in r.text.lower():
            print("🔐 Session expired (login page detected)")
            time.sleep(60)
            continue

        try:
            data = r.json()
        except Exception:
            print("⚠️ JSON parse failed")
            print(r.text[:200])
            time.sleep(CHECK_INTERVAL)
            continue

        rows = data.get("aaData", [])
        if not rows:
            time.sleep(CHECK_INTERVAL)
            continue

        # Oldest → Newest (clean order)
        rows.reverse()

        for row in rows:
            ts, pool, number, service, message = row[:5]
            key = f"{number}_{ts}"

            if key in sent:
                continue

            otp = extract_otp(message)
            print("🧾 SMS:", message)

            if otp:
                msg = (
                    f"🔐 *NEW OTP RECEIVED*\n"
                    f"━━━━━━━━━━━━━━\n"
                    f"🕒 `{ts}`\n"
                    f"📞 `{number}`\n"
                    f"📲 `{service}`\n"
                    f"🔢 *OTP:* `{otp}`\n"
                )
                send_telegram(msg)

            sent.append(key)

        # keep memory small
        sent = sent[-10:]
        save_state({"sent": sent})

    except Exception as e:
        print("💥 ERROR:", e)

    time.sleep(CHECK_INTERVAL)
