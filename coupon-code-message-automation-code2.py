"""
Coupon‑sending automation via AiSensy

"""

import csv
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

# ========== CONFIGURATION ==========
SENSY_API_KEY      = "your_sensy_api_key_here"
SENSY_API_URL      = "https://backend.sensy.ai/sendMessage"
COUPON_EXPIRY_DAYS = 5

# ---------- choose ONE user‑data source ----------
USE_SOURCE   = "csv"                              # "csv"  or  "api"
CSV_PATH     = Path("users.csv")                  # if USE_SOURCE == "csv"
API_ENDPOINT = "https://my-crm/api/users"         # if USE_SOURCE == "api"
# ================================================

# ========== PRE‑DEFINED COUPON CODES ==========
coupon_codes = [ #testing k liye hai bass yeah
    "SAVE-FD1031",
    "SAVE-LT5738",
    "SAVE-XY9042",
    "SAVE-MK2930",
    "SAVE-RJ8831",
    # …list ko jitna chahe lamba rakhein
]
# ==============================================


# ---------- HELPERS ----------
def days_since(date_str: str, fmt: str = "%Y-%m-%d") -> int:
    last = datetime.strptime(date_str, fmt)
    return (datetime.now() - last).days


def get_discount(days: int) -> int:
    slabs = [
        (0,   7,   0),
        (8,   16, 10),
        (17,  30, 25),
        (31,  45, 40),
        (46,  90, 50),
        (91, 120, 65),
        (121,150, 80),
        (151,175, 90),
        (176,365, 95),
    ]
    for low, high, disc in slabs:
        if low <= days <= high:
            return disc
    return 0


def send_coupon_via_sensy(user: Dict, discount: int,
                          coupon_code: str, expiry: datetime) -> bool:
    payload = {
        "to": user["phone"],
        "template": "user_coupon_offer",       # pre‑approved template
        "data": {
            "name":        user["name"],
            "discount":    f"{discount}%",
            "coupon_code": coupon_code,
            "valid_till":  expiry.strftime("%d %b %Y"),
        },
    }
    headers = {
        "Authorization": f"Bearer {SENSY_API_KEY}",
        "Content-Type":  "application/json",
    }
    try:
        resp = requests.post(SENSY_API_URL, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        print(f"[ERROR] {user['phone']} → {e}")
        return False


# ---------- DATA INGESTION ----------
def load_users_from_csv(csv_path: Path) -> List[Dict]:
    records = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["renewed"] = str(row.get("renewed", "")).lower() == "true"
            records.append(row)
    return records


def load_users_from_api(api_url: str) -> List[Dict]:
    resp = requests.get(api_url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_users() -> List[Dict]:
    if USE_SOURCE == "csv":
        return load_users_from_csv(CSV_PATH)
    if USE_SOURCE == "api":
        return load_users_from_api(API_ENDPOINT)
    raise ValueError(f"Unknown data source '{USE_SOURCE}'.")


# ---------- MAIN PIPELINE ----------
def main() -> None:
    users = get_users()
    for user in users:
        if user.get("renewed"):
            continue

        days = days_since(user["last_recharge"])
        discount = get_discount(days)
        if discount == 0:
            continue

        # ==== COUPON ASSIGNMENT ====
        if not coupon_codes:
            print(f"⚠️  No coupons left → Skipping {user['name']} ({user['phone']})")
            continue

        coupon_code = coupon_codes.pop(0)               # FIFO
        expiry_date = datetime.now() + timedelta(days=COUPON_EXPIRY_DAYS)

        success = send_coupon_via_sensy(
            user,
            discount,
            coupon_code,
            expiry_date,
        )

        status = "✅ SENT" if success else "❌ FAILED"
        print(
            f"{status} → {user['name']} ({user['phone']}): "
            f"{coupon_code} | {discount}% | valid till {expiry_date:%d-%b-%Y}"
        )


if __name__ == "__main__":
    main()
