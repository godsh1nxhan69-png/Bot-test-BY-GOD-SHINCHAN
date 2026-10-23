import requests
import json
import time

# ==============================
# CONFIGURATION
# ==============================
BOT_TOKEN = ""           # <- 8205360993:AAGyGGuoXAwSeiX3RWlixFwQn7CXCiI-6ps
EXTERNAL_API_URL = ""    # <- e.g. "https://localhost:8443/lookup?number="

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ==============================
# KEYBOARD
# ==============================
PHONE_KEYBOARD = {
    "keyboard": [
        [{"text": "📱 Phone Lookup"}]
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False
}

REMOVE_KEYBOARD = {"remove_keyboard": True}

# ==============================
# HELPER FUNCTIONS
# ==============================

def send_message(chat_id, text, reply_markup=None):
    """Send a message via Telegram Bot API manually."""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)

    try:
        response = requests.post(f"{BASE_URL}/sendMessage", data=payload, timeout=10)
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] send_message failed: {e}")
        return None


def get_updates(offset=None, timeout=30):
    """Poll Telegram for updates using long polling."""
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset

    try:
        response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=timeout + 10)
        return response.json()
    except requests.RequestException as e:
        print(f"[ERROR] get_updates failed: {e}")
        return {"ok": False, "result": []}


def fetch_phone_data(number):
    """Call the external API and return parsed JSON."""
    url = f"{EXTERNAL_API_URL}{number}" if EXTERNAL_API_URL.endswith(("=", "/")) else f"{EXTERNAL_API_URL}?number={number}"
    try:
        response = requests.get(url, timeout=15, verify=False)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": f"External API request failed: {e}"}
    except ValueError:
        return {"error": "External API did not return valid JSON."}


def format_pre(data):
    """Format API response inside an HTML <pre> tag."""
    pretty = json.dumps(data, indent=2, ensure_ascii=False)
    return f"<pre>{pretty}</pre>"


# ==============================
# MAIN LOOP (offset-based polling)
# ==============================

def main():
    print("🤖 Bot started. Press Ctrl+C to stop.")
    offset = 0
    awaiting_number = set()  # chat_ids waiting for a phone number

    while True:
        updates = get_updates(offset=offset)

        if not updates.get("ok"):
            time.sleep(3)
            continue

        for update in updates.get("result", []):
            offset = update["update_id"] + 1  # confirm processed update

            if "message" not in update:
                continue

            message = update["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "").strip()

            # ---- /start command ----
            if text == "/start":
                welcome = (
                    "👋 <b>Welcome!</b>\n\n"
                    "I'm a phone lookup bot. Tap the button below to get started."
                )
                send_message(chat_id, welcome, reply_markup=PHONE_KEYBOARD)
                awaiting_number.discard(chat_id)

            # ---- Keyboard button pressed ----
            elif text == "📱 Phone Lookup":
                send_message(chat_id, "📞 Send 10 digit mobile number:")
                awaiting_number.add(chat_id)

            # ---- Waiting for number input ----
            elif chat_id in awaiting_number:
                if text.isdigit() and len(text) == 10:
                    send_message(chat_id, "🔍 Looking up number, please wait...")
                    data = fetch_phone_data(text)
                    send_message(chat_id, format_pre(data))
                    awaiting_number.discard(chat_id)
                else:
                    send_message(
                        chat_id,
                        "❌ <b>Invalid input.</b>\n"
                        "Please send a valid <b>10 digit numeric</b> mobile number.\n"
                        "Example: <code>9876543210</code>"
                    )

            # ---- Unknown command / message ----
            else:
                send_message(
                    chat_id,
                    "🤔 I didn't understand that.\nUse /start or tap 📱 Phone Lookup."
                )

        time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped.")
                             
