import requests
import random
import string
from datetime import datetime

# ========== CONFIGURATION ==========

# AiSensy API endpoint
SENSY_API_URL = "https://backend.aisensy.com/sendMessage"

# Replace this with your actual AiSensy API key
SENSY_API_KEY = "your_aisensy_api_key"

# HTTP headers for AiSensy API
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {SENSY_API_KEY}"
}

# ========== FUNCTION: Generate Unique Coupon Code ==========

def generate_coupon_code(length=8):
    """
    Creates a random alphanumeric coupon code of specified length.
    Default is 8 characters (e.g., 'X7J9LKD2')
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ========== SLAB LOGIC: Discount Based on Days Passed ==========

# List of slabs: (min_day, max_day, discount_percent)
DISCOUNT_SLABS = [
    (8, 16, 10),
    (17, 30, 25),
    (31, 45, 40),
    (46, 90, 50),
    (91, 120, 65),
    (121, 150, 80),
    (151, 175, 90),
    (176, 365, 95)
]

def get_discount(days):
    """
    Finds the correct discount slab based on number of days passed since last recharge.
    Returns discount percentage, or None if no discount is applicable.
    """
    for min_day, max_day, discount in DISCOUNT_SLABS:
        if min_day <= days <= max_day:
            return discount
    return None  # No discount if days < 8 or > 365

# ========== MAIN FUNCTION: Send Coupon via AiSensy API ==========

def send_coupon(user):
    """
    Sends a discount coupon via WhatsApp using AiSensy,
    based on the number of days since the user's last recharge.
    """
    phone = user['phone']  # User's WhatsApp number with country code
    name = user.get('name', "there")  # Default fallback name
    last_recharge = datetime.strptime(user['last_recharge'], "%Y-%m-%d")  # Convert string date to datetime
    today = datetime.today()
    
    # Calculate how many days have passed since last recharge
    days_passed = (today - last_recharge).days

    # Get discount percentage using slab logic
    discount = get_discount(days_passed)

    # Skip sending if user is not eligible for discount
    if discount is None:
        return None

    # Generate a unique coupon code for this user
    coupon_code = generate_coupon_code()

    # Prepare WhatsApp message payload as per AiSensy template
    payload = {
        "phone": phone,
        "template_name": "discount_coupon",  # Template must be pre-approved in AiSensy
        "template_data": {
            "name": name,
            "discount": f"{discount}%",
            "coupon": coupon_code
        }
    }

    # Send POST request to AiSensy API
    response = requests.post(SENSY_API_URL, headers=HEADERS, json=payload)

    # Return the API status and response JSON
    return response.status_code, response.json()

# ========== SAMPLE USERS LIST ==========

# List of users with phone number and last recharge date
users = [
    {"phone": "91XXXXXXXXXX", "name": "Alok", "last_recharge": "2024-11-20"},
    {"phone": "91YYYYYYYYYY", "name": "Vishwas", "last_recharge": "2024-12-30"},
    # Add more user dictionaries here...
]

# ========== LOOP: Send Coupons to All Eligible Users ==========

for user in users:
    result = send_coupon(user)
    print(f"Sent to {user['phone']}: {result}")
