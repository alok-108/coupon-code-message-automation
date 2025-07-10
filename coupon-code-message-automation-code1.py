import csv
import requests
from datetime import datetime, timedelta
import pandas as pd

# ========== CONFIGURATION ==========
SENSY_API_KEY = 'your_sensy_api_key_here'
SENSY_API_URL = 'https://backend.sensy.ai/sendMessage'
USER_API_URL = 'https://example.com/api/users'  # Replace with your API endpoint
USE_SOURCE = 'csv'  # 'csv' or 'api'
CSV_FILE_PATH = 'users.csv'
COUPON_EXPIRY_DAYS = 5

# ========== PRE-DEFINED COUPON CODES ==========
coupon_codes = [
    "SAVE-XA1234",
    "SAVE-ZB5678",
    "SAVE-QT9012",
    "SAVE-UV3456",
    "SAVE-MN7890",
    # Add as many as needed
]

# ========== FUNCTIONS ==========

def days_since(date_str):
    last = datetime.strptime(date_str, "%Y-%m-%d")
    return (datetime.now() - last).days

def get_discount(days):
    if 0 <= days <= 7: return 0
    elif 8 <= days <= 16: return 10
    elif 17 <= days <= 30: return 25
    elif 31 <= days <= 45: return 40
    elif 46 <= days <= 90: return 50
    elif 91 <= days <= 120: return 65
    elif 121 <= days <= 150: return 80
    elif 151 <= days <= 175: return 90
    elif 176 <= days <= 365: return 95
    return 0

def send_coupon_via_sensy(user, discount, coupon_code, expiry):
    payload = {
        "to": user["phone"],
        "template": "user_coupon_offer",  # Pre-approved template name
        "data": {
            "name": user["name"],
            "discount": f"{discount}%",
            "coupon_code": coupon_code,
            "valid_till": expiry.strftime("%d %b %Y")
        }
    }

    headers = {
        "Authorization": f"Bearer {SENSY_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(SENSY_API_URL, json=payload, headers=headers)
        return response.status_code, response.json()
    except Exception as e:
        return 500, {"error": str(e)}

# ========== USER DATA LOADERS ==========

def load_users_from_csv(filepath):
    users = []
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            row['renewed'] = row['renewed'].strip().lower() == 'true'
            users.append(row)
    return users

def load_users_from_api(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print("❌ API fetch failed:", response.status_code)
            return []
    except Exception as e:
        print("❌ API error:", str(e))
        return []

def update_csv_renewed_status(filepath, updated_users):
    df = pd.read_csv(filepath)
    for user in updated_users:
        df.loc[df['user_id'] == int(user['user_id']), 'renewed'] = True
    df.to_csv(filepath, index=False)

# ========== MAIN LOGIC ==========

if __name__ == "__main__":
    # Step 1: Load users
    if USE_SOURCE == 'csv':
        users = load_users_from_csv(CSV_FILE_PATH)
    elif USE_SOURCE == 'api':
        users = load_users_from_api(USER_API_URL)
    else:
        print("❌ Invalid data source selected!")
        exit()

    sent_users = []

    # Step 2: Iterate and send coupon
    for user in users:
        if not user["renewed"]:
            days = days_since(user["last_recharge"])
            discount = get_discount(days)

            if discount == 0:
                continue

            # Coupon exhaustion check
            if not coupon_codes:
                print(f"⚠️ No coupons left for {user['name']} ({user['phone']}) — Skipping")
                continue

            coupon_code = coupon_codes.pop(0)
            expiry_date = datetime.now() + timedelta(days=COUPON_EXPIRY_DAYS)

            status_code, result = send_coupon_via_sensy(user, discount, coupon_code, expiry_date)

            if status_code == 200:
                print(f"✅ Sent to {user['name']} ({user['phone']}): {coupon_code} ({discount}%)")
                sent_users.append(user)
            else:
                print(f"❌ Failed for {user['name']} ➤ Status: {status_code} ➤ {result}")

    # Step 3: Update CSV if needed
    if USE_SOURCE == 'csv' and sent_users:
        update_csv_renewed_status(CSV_FILE_PATH, sent_users)
        print("📁 CSV updated with renewed status.")
