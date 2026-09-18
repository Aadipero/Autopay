import asyncio
import datetime
import io
import json
import logging
import random
import sqlite3
import time
import urllib.parse
from PIL import Image, ImageDraw
import requests
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =====================================================================
# 1. CONFIGURATION & CREDENTIALS
# =====================================================================
BOT_TOKEN = "8834297340:AAGZO1_5oK90SOM2m2IPC19YQYOpi8_6EKk"          # Apna Telegram Bot Token yahan dalein
ADMIN_ID = 8423151783                     # Apna numeric Admin ID yahan dalein

# AAPKI BHARATPE DETAILS
YOUR_UPI_ID = "BHARATPE2M0R0D2G3L60733@unitype"

# EKUPI GATEWAY DETAILS
GATEWAY_URL = "https://api.ekupi.in/api/check-order-status"
GATEWAY_CREATE_URL = "https://api.ekupi.in/api/create-order"
GATEWAY_API_KEY = "GMC-1043-69D7EC-7935FE"

BOT_CREDIT_TAG = "⚡ <b>Avengers Shop</b> | Built by @YourUsername"

ORDER_TIMEOUT_SECONDS = 300
PARTY_POPPER_EFFECT_ID = 5046509860389126442
LOW_STOCK_THRESHOLD = 5

PROOF_CHANNEL_ID = -1001234567890  # Proof channel ID yahan dalein

FORCE_SUB_CHANNELS = [
    {
        "id": -1001234567890,
        "title": "Channel 1 Title",
        "link": "https://t.me/your_channel_1"
    },
    {
        "id": -1009876543210,
        "title": "Channel 2 Title",
        "link": "https://t.me/your_channel_2"
    }
]

# =====================================================================
# 2. CUSTOM EMOJIS & THEME
# =====================================================================
CUSTOM_EMOJI_IDS = [
    "5370784581341422520",
    "5274026806477857971",
    "5363992034728229166",
    "5197304993920616826",
    "5193209274452425995",
    "5427225953463972959",
    "5350619413533958825",
    "5415612280291205341",
    "5260463209562776385",
    "5273914604752216432",
    "5373135805353041178",
    "5371071931833393000",
    "6267229004311303657",
    "6267039884016358504",
    "6267225207560214192",
    "6267140231632262769",
    "6267144651153609853",
    "6264989883241076562",
    "6266967801580231067",
    "6267129592998270736"
]

def custom_emoji_text(idx: int, fallback: str = "🔹") -> str:
    if 0 <= idx < len(CUSTOM_EMOJI_IDS):
        return f'<tg-emoji emoji-id="{CUSTOM_EMOJI_IDS[idx]}">{fallback}</tg-emoji>'
    return fallback

CE_SHOP    = custom_emoji_text(0, "🛒")
CE_BOX     = custom_emoji_text(1, "📦")
CE_WALLET  = custom_emoji_text(2, "💳")
CE_SEARCH  = custom_emoji_text(3, "🔍")
CE_SUPPORT = custom_emoji_text(4, "🎧")
CE_GUIDE   = custom_emoji_text(5, "📘")
CE_ADMIN   = custom_emoji_text(6, "👑")
CE_VERIFY  = custom_emoji_text(7, "⚡")
CE_SUCCESS = custom_emoji_text(8, "✅")
CE_FAIL    = custom_emoji_text(9, "❌")
CE_ALERT   = custom_emoji_text(10, "🔔")
CE_FIRE    = custom_emoji_text(11, "🔥")
CE_SPARKLE = custom_emoji_text(12, "✨")
CE_KEY     = custom_emoji_text(13, "🔑")
CE_CLOCK   = custom_emoji_text(14, "⏱️")
CE_CHART   = custom_emoji_text(15, "📊")
CE_GIFT    = custom_emoji_text(16, "🎁")
CE_RADIO   = custom_emoji_text(17, "📢")
CE_TAG     = custom_emoji_text(18, "🏷️")
CE_STAR    = custom_emoji_text(19, "⭐")

DEYMON_BLUE_PRIMARY = "#00d2ff"
DEYMON_BLUE_SECONDARY = "#3a7bd5"
DEYMON_BLUE_DARK = "#0a1128"
DEYMON_BLUE_CARD = "#101f42"
DEYMON_BLUE_TEXT = "#e0f2fe"
DEYMON_BLUE_LINE = "#0284c7"

VERIFY_ATTEMPTS = {}
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

def get_ist_now():
    return datetime.datetime.now(IST)

def make_timer_button(remaining_sec):
    if remaining_sec <= 0:
        return "⌛ Expired"
    mins, secs = divmod(remaining_sec, 60)
    return f"⏱️ {mins:02d}:{secs:02d} Left"

# =====================================================================
# 3. DATABASE ENGINE
# =====================================================================
def init_db():
    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            format_type TEXT NOT NULL DEFAULT 'text',
            price REAL DEFAULT 0,
            max_buy INTEGER DEFAULT 10,
            flash_price REAL DEFAULT 0,
            flash_expiry INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            item_data TEXT NOT NULL,
            session_key TEXT,
            is_sold INTEGER DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_code TEXT UNIQUE,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            total_price REAL,
            created_at INTEGER,
            delivered_data TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            joined_at INTEGER,
            is_banned INTEGER DEFAULT 0,
            wallet_balance REAL DEFAULT 0.0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS restock_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            user_id INTEGER,
            UNIQUE(product_id, user_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS bulk_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            min_qty INTEGER,
            unit_price REAL,
            UNIQUE(product_id, min_qty)
        )
    """)
    conn.commit()
    conn.close()

init_db()

def is_rate_limited(uid: int) -> bool:
    now = time.time()
    history = VERIFY_ATTEMPTS.get(uid, [])
    history = [t for t in history if now - t < 30]
    if len(history) >= 3:
        VERIFY_ATTEMPTS[uid] = history
        return True
    history.append(now)
    VERIFY_ATTEMPTS[uid] = history
    return False

def get_effective_price(product_id: int, base_price: float, qty: int) -> tuple[float, float, float]:
    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("SELECT flash_price, flash_expiry FROM products WHERE id = ?", (product_id,))
    p_row = c.fetchone()
    now_ts = int(time.time())
    
    flash_p = float(p_row[0] or 0) if p_row else 0
    flash_exp = int(p_row[1] or 0) if p_row else 0

    if flash_p > 0 and flash_exp > now_ts:
        effective_unit_price = flash_p
    else:
        c.execute("SELECT min_qty, unit_price FROM bulk_rates WHERE product_id = ? AND min_qty <= ? ORDER BY min_qty DESC LIMIT 1", (product_id, qty))
        b_row = c.fetchone()
        effective_unit_price = float(b_row[1]) if b_row else float(base_price or 0)
    conn.close()

    total_amount = round(effective_unit_price * qty, 2)
    standard_total = round((base_price or 0) * qty, 2)
    savings = round(max(0.0, standard_total - total_amount), 2)
    return total_amount, effective_unit_price, savings

async def check_low_stock(bot, product_id: int, product_name: str):
    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM stock WHERE product_id = ? AND is_sold = 0", (product_id,))
    remaining = c.fetchone()[0]
    conn.close()

    if remaining <= LOW_STOCK_THRESHOLD:
        alert_text = (
            f"{CE_ALERT} <b>[ LOW STOCK ALERT ]</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{CE_BOX} <b>Product:</b> <code>{product_name}</code>\n"
            f"⚠️ <b>Remaining:</b> <code>{remaining} units</code>\n"
            f"Please restock soon."
        )
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=alert_text, parse_mode="HTML")
        except Exception:
            pass

async def hourly_stock_broadcast_loop(bot):
    await asyncio.sleep(15)
    while True:
        try:
            conn = sqlite3.connect("store.db")
            c = conn.cursor()
            c.execute("""
                SELECT p.name, p.price,
                       (SELECT COUNT(*) FROM stock WHERE product_id = p.id AND is_sold = 0) as avail
                FROM products p
            """)
            products = c.fetchall()
            conn.close()

            if products:
                now_ist = get_ist_now().strftime("%I:%M %p IST")
                body_lines = []
                for name, price, avail in products:
                    if avail > 0:
                        body_lines.append(f"🟢 <b>{name}</b> — ₹{price} (<code>{avail} left</code>)")
                    else:
                        body_lines.append(f"🔴 <b>{name}</b> — ₹{price} (<i>Out of stock</i>)")

                block_content = "\n".join(body_lines)
                msg_text = (
                    f"{CE_VERIFY} <b>AVENGERS SHOP LIVE INVENTORY</b> {CE_SPARKLE}\n"
                    f"🕒 <b>Synced:</b> <code>{now_ist}</code>\n\n"
                    f"<blockquote>{block_content}</blockquote>\n\n"
                    f"{BOT_CREDIT_TAG}"
                )

                bot_obj = await bot.get_me()
                buy_button = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🛍️ Buy Vouchers", url=f"https://t.me/{bot_obj.username}?start=buy")]
                ])

                await bot.send_message(
                    chat_id=PROOF_CHANNEL_ID,
                    text=msg_text,
                    reply_markup=buy_button,
                    parse_mode="HTML"
                )
        except Exception as e:
            logging.error(f"Stock broadcast failed: {e}")
        await asyncio.sleep(3600)

async def delete_qr_after_timeout(bot, chat_id, message_id, order_code, delay_sec=300):
    await asyncio.sleep(delay_sec)
    try:
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT status FROM orders WHERE order_code = ?", (order_code,))
        row = c.fetchone()
        if row and row[0] == "pending":
            c.execute("UPDATE orders SET status = 'expired' WHERE order_code = ?", (order_code,))
            conn.commit()
            is_pending = True
        else:
            is_pending = False
        conn.close()

        if is_pending:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except Exception:
                pass
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=f"{CE_CLOCK} Order <code>{order_code}</code> expired after 5 minutes and was securely cleared.",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    except Exception as e:
        logging.error(f"QR timeout cleanup error: {e}")

def _session_id_of(raw: str):
    try:
        obj = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(obj, dict):
            for k in ("user_id", "mobile", "phone", "id", "session_id"):
                v = obj.get(k)
                if v is not None:
                    return f"{k}:{v}"
    except Exception:
        pass
    return None

def extract_all_json_objects(text: str) -> list:
    results = []
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    results.append(json.dumps(item, ensure_ascii=False))
            if results:
                return results
        elif isinstance(parsed, dict):
            return [json.dumps(parsed, ensure_ascii=False)]
    except Exception:
        pass

    decoder = json.JSONDecoder()
    pos = 0
    length = len(text)
    while pos < length:
        while pos < length and text[pos] != '{':
            pos += 1
        if pos >= length:
            break
        try:
            obj, end = decoder.raw_decode(text[pos:])
            if isinstance(obj, dict):
                results.append(json.dumps(obj, ensure_ascii=False))
            pos += end
        except json.JSONDecodeError:
            pos += 1
    return results

def is_user_banned(uid: int) -> bool:
    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("SELECT is_banned FROM users WHERE user_id = ?", (uid,))
    row = c.fetchone()
    conn.close()
    return bool(row and row[0] == 1)

async def check_user_joined_all(bot, user_id: int) -> tuple[bool, list]:
    if user_id == ADMIN_ID:
        return True, []
    missing = []
    for ch in FORCE_SUB_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
            if member.status in ["left", "kicked"]:
                missing.append(ch)
        except Exception:
            pass
    return (len(missing) == 0), missing

async def get_force_sub_keyboard(bot):
    kb = []
    for ch in FORCE_SUB_CHANNELS:
        try:
            chat = await bot.get_chat(ch["id"])
            link = chat.invite_link or ch.get("link")
            if not link:
                link = await bot.export_chat_invite_link(ch["id"])
        except Exception:
            link = ch.get("link")
        kb.append([InlineKeyboardButton(f"🔹 Join {ch['title']}", url=link)])

    kb.append([InlineKeyboardButton("✅ I've Joined — Verify", callback_data="verify_force_join")])
    return InlineKeyboardMarkup(kb)

# --- FORMAT ROUTED DISPATCHER ---
async def deliver_voucher_to_user(uid: int, codes: list, product_name: str, order_code: str, fmt: str, bot):
    guidelines = (
        f"<blockquote>"
        f"⚠️ <b>Use immediately to avoid expiration.</b>\n"
        f"• All items guaranteed authentic & verified.\n"
        f"• Mandatory video proof from bot purchase till app activation.\n"
        f"• No uncut video = No replacement.\n"
        f"</blockquote>\n\n"
        f"{BOT_CREDIT_TAG}"
    )

    if fmt == "session":
        if len(codes) <= 10:
            for i, code in enumerate(codes, 1):
                file_bytes = io.BytesIO(code.encode("utf-8"))
                file_bytes.name = f"session_{i}.txt"
                cap = f"{CE_VERIFY} <b>Session Delivered:</b> <code>{product_name}</code>\nOrder ID: <code>{order_code}</code>\nItem: {i}/{len(codes)}\n\n{guidelines}"
                try:
                    await bot.send_document(chat_id=uid, document=file_bytes, caption=cap, parse_mode="HTML")
                except Exception:
                    await bot.send_document(chat_id=uid, document=file_bytes, caption=f"Session {i}/{len(codes)}")
        else:
            file_content = "\n\n".join(codes)
            file_bytes = io.BytesIO(file_content.encode("utf-8"))
            file_bytes.name = f"bulk_sessions_{len(codes)}.txt"
            cap = f"{CE_VERIFY} <b>Bulk Sessions Delivered:</b> <code>{product_name}</code>\nOrder ID: <code>{order_code}</code>\nTotal: {len(codes)} records\n\n{guidelines}"
            await bot.send_document(chat_id=uid, document=file_bytes, caption=cap, parse_mode="HTML")
    else:
        formatted_codes = "\n".join([f"<code>{c}</code>" for c in codes])
        delivery_msg = (
            f"{CE_SUCCESS} <b>VOUCHER DELIVERED SUCCESSFULLY!</b>\n\n"
            f"<blockquote>"
            f"{CE_BOX} <b>Product:</b> <code>{product_name}</code>\n"
            f"🆔 <b>Order ID:</b> <code>{order_code}</code>"
            f"</blockquote>\n\n"
            f"{CE_KEY} <b>Your Codes:</b>\n<blockquote>{formatted_codes}</blockquote>\n\n"
            f"{guidelines}"
        )
        try:
            await bot.send_message(
                chat_id=uid,
                text=delivery_msg,
                message_effect_id=PARTY_POPPER_EFFECT_ID,
                parse_mode="HTML"
            )
        except Exception:
            await bot.send_message(chat_id=uid, text=delivery_msg, parse_mode="HTML")

# =====================================================================
# EKUPI PAYMENT VERIFICATION (BHARATPE CONNECTED)
# =====================================================================
def verify_payment_gateway(order_id, expected_amount):
    payload = {
        "key": GATEWAY_API_KEY,
        "client_txn_id": order_id
    }
    try:
        res = requests.post(GATEWAY_URL, json=payload, timeout=10)
        data = res.json()
        
        if data.get("status") is True:
            txn_data = data.get("data", {})
            txn_status = str(txn_data.get("status", "")).lower()

            if txn_status in ["success", "completed", "paid"]:
                paid_val = float(txn_data.get("amount", expected_amount))
                exp_val = float(expected_amount)
                
                if abs(paid_val - exp_val) > 0.01 and paid_val < exp_val:
                    return False, f"AMOUNT_MISMATCH (Expected: ₹{exp_val}, Paid: ₹{paid_val})", paid_val
                
                return True, "SUCCESS", paid_val
            else:
                return False, "PAYMENT_NOT_FOUND", 0.0

        return False, "PAYMENT_NOT_FOUND", 0.0
    except Exception as e:
        logging.error(f"Gateway verify exception: {e}")
        return False, f"GATEWAY_ERROR: {e}", 0.0

# =====================================================================
# 4. DEYMON BLUE POSTER GENERATOR
# =====================================================================
def generate_avengers_qr_poster(upi_string, amount, order_code, product_name, expiry_str):
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=320x320&data={urllib.parse.quote(upi_string)}&color=000000&bgcolor=ffffff&qzone=2&format=png"
    resp = requests.get(qr_url, timeout=10)
    qr_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")

    width, height = 500, 670
    poster = Image.new("RGBA", (width, height), DEYMON_BLUE_DARK)
    draw = ImageDraw.Draw(poster)

    draw.rectangle([(5, 5), (width - 6, height - 6)], outline=DEYMON_BLUE_PRIMARY, width=3)
    draw.rectangle([(8, 8), (width - 9, height - 9)], outline=DEYMON_BLUE_SECONDARY, width=1)

    draw.rectangle([(0, 0), (width, 68)], fill=DEYMON_BLUE_CARD)
    draw.text((width // 2, 34), "⚡ AVENGERS SECURE GATEWAY ⚡", fill=DEYMON_BLUE_PRIMARY, anchor="mm")

    draw.text((width // 2, 88), f"ITEM: {str(product_name)[:30].upper()}", fill="#ffffff", anchor="mm")
    draw.text((width // 2, 112), f"ORDER CODE: {order_code}", fill=DEYMON_BLUE_TEXT, anchor="mm")

    draw.rectangle([(85, 134), (415, 464)], fill="#ffffff", outline=DEYMON_BLUE_PRIMARY, width=2)
    poster.paste(qr_img, (90, 139))

    draw.rectangle([(30, 480), (width - 30, 540)], fill=DEYMON_BLUE_CARD, outline=DEYMON_BLUE_PRIMARY, width=2)
    draw.text((width // 2, 510), f"EXACT PAYABLE: Rs. {amount:.2f}", fill="#ffffff", anchor="mm")

    draw.text((width // 2, 565), "Scan via Paytm / PhonePe / GPay", fill="#94a3b8", anchor="mm")
    draw.rectangle([(40, 590), (width - 40, 635)], fill="#1e293b", outline=DEYMON_BLUE_LINE, width=2)
    draw.text((width // 2, 604), "⚠️ STRICT 5-MINUTE AUTO-LOCK", fill="#f87171", anchor="mm")
    draw.text((width // 2, 622), f"EXPIRES PROMPTLY AT: {expiry_str}", fill=DEYMON_BLUE_PRIMARY, anchor="mm")

    out = io.BytesIO()
    poster.save(out, format="PNG")
    out.seek(0)
    return out

# --- KEYBOARDS ---
def get_user_keyboard(user_id):
    kb = [
        [KeyboardButton("🛍️ Buy Vouchers"), KeyboardButton("📦 My Orders")],
        [KeyboardButton("💳 My Wallet"), KeyboardButton("🔍 Recover Voucher")],
        [KeyboardButton("🎫 Support"), KeyboardButton("📖 How to Use")]
    ]
    if user_id == ADMIN_ID:
        kb.append([KeyboardButton("👑 Admin Console")])
    return ReplyKeyboardMarkup(kb, resize_keyboard=True)

def get_seller_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("➕ Add Product"), KeyboardButton("📦 Stock Manager")],
        [KeyboardButton("🔥 Flash Sale"), KeyboardButton("🔄 Replace By Order ID")],
        [KeyboardButton("🎁 Free Code"), KeyboardButton("📊 Sales Dashboard")],
        [KeyboardButton("📢 Mass Broadcast"), KeyboardButton("🚫 Ban / Unban User")],
        [KeyboardButton("🧹 Purge Sold Stock"), KeyboardButton("🔙 Exit to Home")]
    ], resize_keyboard=True)

def get_product_manage_kb(pid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Rename", callback_data=f"edname_{pid}"), InlineKeyboardButton("💰 Base Price", callback_data=f"edprice_{pid}")],
        [InlineKeyboardButton("📊 Bulk Rates", callback_data=f"mngbulk_{pid}"), InlineKeyboardButton("🔢 Max Buy", callback_data=f"edmax_{pid}")],
        [InlineKeyboardButton("🔑 Load Stock", callback_data=f"addstk_{pid}"), InlineKeyboardButton("❌ Remove Product", callback_data=f"delprod_{pid}")],
        [InlineKeyboardButton("⬅️ Back", callback_data="list_prods")]
    ])

def get_qty_keyboard_with_bulk(pid, max_available, unit_price):
    final_amt, eff_price, savings = get_effective_price(pid, unit_price, 1)
    tag = f"🔥 1 Qty — ₹{final_amt}" if savings > 0 else f"🟢 1 Qty — ₹{final_amt}"
    
    buttons = [
        [InlineKeyboardButton(tag, callback_data=f"setqty_{pid}_1")],
        [InlineKeyboardButton("✏️ Custom Quantity", callback_data=f"customqty_{pid}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")]
    ]
    return InlineKeyboardMarkup(buttons)

async def create_wallet_recharge_invoice(target_message, context, uid, amount):
    random_paisa = random.randint(30, 90) / 100.0
    total_amount = round(amount + random_paisa, 2)
    order_code = f"WAL-{int(time.time())}"
    now_ts = int(time.time())
    
    now_ist = get_ist_now()
    expiry_dt = now_ist + datetime.timedelta(seconds=ORDER_TIMEOUT_SECONDS)
    expiry_time_str = expiry_dt.strftime("%I:%M:%S %p IST")

    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO orders (order_code, user_id, product_id, quantity, total_price, created_at, status)
        VALUES (?, ?, 0, 1, ?, ?, 'pending')
    """, (order_code, uid, total_amount, now_ts))
    conn.commit()
    conn.close()

    context.user_data.clear()

    # EkUPI dynamic intent try karein, fallback direct UPI
    upi_string = f"upi://pay?pa={YOUR_UPI_ID}&pn=AvengersShop&am={total_amount}&cu=INR&tr={order_code}&tn={order_code}"
    try:
        gw_payload = {
            "key": GATEWAY_API_KEY,
            "client_txn_id": order_code,
            "amount": str(total_amount),
            "p_info": "Wallet Topup",
            "customer_name": f"User_{uid}",
            "customer_email": "user@store.bot",
            "customer_mobile": "9999999999",
            "redirect_url": "https://t.me/"
        }
        res = requests.post(GATEWAY_CREATE_URL, json=gw_payload, timeout=5).json()
        if res.get("status") is True and res.get("data", {}).get("payment_url"):
            upi_string = res["data"]["payment_url"]
    except Exception:
        pass

    poster_bytes = generate_avengers_qr_poster(upi_string, total_amount, order_code, "WALLET TOPUP", expiry_time_str)
    timer_text = make_timer_button(ORDER_TIMEOUT_SECONDS)

    caption = (
        f"{CE_WALLET} <b>[ WALLET RECHARGE ]</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>"
        f"🆔 <b>Order ID:</b> <code>{order_code}</code> <i>(Tap to copy)</i>\n"
        f"💳 <b>Top-Up Amount:</b> <code>₹{amount}</code>\n"
        f"💰 <b>Pay Exact:</b> <code>{total_amount}</code> <i>(Tap to copy)</i>"
        f"</blockquote>\n\n"
        f"👉 Scan QR code and complete payment."
    )

    kb = [
        [InlineKeyboardButton("✅ I Have Paid", callback_data=f"chkpay_{order_code}")],
        [InlineKeyboardButton(timer_text, callback_data=f"refreshtime_{order_code}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")]
    ]

    if hasattr(target_message, 'reply_photo'):
        sent_msg = await target_message.reply_photo(photo=poster_bytes, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        sent_msg = await target_message.message.reply_photo(photo=poster_bytes, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

    asyncio.create_task(delete_qr_after_timeout(context.bot, uid, sent_msg.message_id, order_code, ORDER_TIMEOUT_SECONDS))

async def create_and_send_invoice(target_message, context, uid, pid, qty):
    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM stock WHERE product_id = ? AND is_sold = 0", (pid,))
    available_stock = c.fetchone()[0]
    if available_stock < qty:
        conn.close()
        msg = f"{CE_FAIL} Stock kam pad gaya hai! Sirf <code>{available_stock}</code> units bache hain."
        if hasattr(target_message, 'reply_text'):
            await target_message.reply_text(msg, parse_mode="HTML")
        else:
            await target_message.message.reply_text(msg, parse_mode="HTML")
        return

    c.execute("SELECT name, price FROM products WHERE id = ?", (pid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return
    pname, unit_price = row

    c.execute("SELECT wallet_balance FROM users WHERE user_id = ?", (uid,))
    w_row = c.fetchone()
    user_balance = float(w_row[0]) if w_row and w_row[0] else 0.0
    conn.close()

    discounted_base, eff_price, savings = get_effective_price(pid, unit_price, qty)
    random_paisa = random.randint(30, 90) / 100.0
    total_amount = round(discounted_base + random_paisa, 2)

    order_code = f"AVG-{int(time.time())}"
    now_ts = int(time.time())
    
    now_ist = get_ist_now()
    expiry_dt = now_ist + datetime.timedelta(seconds=ORDER_TIMEOUT_SECONDS)
    expiry_time_str = expiry_dt.strftime("%I:%M:%S %p IST")

    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO orders (order_code, user_id, product_id, quantity, total_price, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    """, (order_code, uid, pid, qty, total_amount, now_ts))
    conn.commit()
    conn.close()

    context.user_data.clear()

    # EkUPI dynamic intent link try karein
    upi_string = f"upi://pay?pa={YOUR_UPI_ID}&pn=AvengersShop&am={total_amount}&cu=INR&tr={order_code}&tn={order_code}"
    try:
        gw_payload = {
            "key": GATEWAY_API_KEY,
            "client_txn_id": order_code,
            "amount": str(total_amount),
            "p_info": pname,
            "customer_name": f"User_{uid}",
            "customer_email": "user@store.bot",
            "customer_mobile": "9999999999",
            "redirect_url": "https://t.me/"
        }
        res = requests.post(GATEWAY_CREATE_URL, json=gw_payload, timeout=5).json()
        if res.get("status") is True and res.get("data", {}).get("payment_url"):
            upi_string = res["data"]["payment_url"]
    except Exception:
        pass

    poster_bytes = generate_avengers_qr_poster(upi_string, total_amount, order_code, pname, expiry_time_str)
    timer_text = make_timer_button(ORDER_TIMEOUT_SECONDS)

    caption = (
        f"{CE_VERIFY} <b>[ AVENGERS PAYMENT INVOICE ]</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>"
        f"🆔 <b>Order ID:</b> <code>{order_code}</code> <i>(Tap to copy)</i>\n"
        f"{CE_BOX} <b>Item:</b> <code>{pname}</code> (x{qty})\n"
        f"💰 <b>Pay Exact:</b> <code>{total_amount}</code> <i>(Tap to copy)</i>"
        f"</blockquote>\n\n"
        f"👉 QR scan karein aur exact payment execute karein."
    )

    kb = []
    if user_balance >= total_amount:
        kb.append([InlineKeyboardButton(f"⚡ Pay via Wallet (₹{user_balance:.2f})", callback_data=f"paywallet_{order_code}")])
    kb.append([InlineKeyboardButton("✅ I Have Paid", callback_data=f"chkpay_{order_code}")])
    kb.append([InlineKeyboardButton(timer_text, callback_data=f"refreshtime_{order_code}")])
    kb.append([InlineKeyboardButton("❌ Cancel Order", callback_data="cancel_order")])
    
    if hasattr(target_message, 'reply_photo'):
        sent_msg = await target_message.reply_photo(photo=poster_bytes, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
    else:
        sent_msg = await target_message.message.reply_photo(photo=poster_bytes, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

    asyncio.create_task(delete_qr_after_timeout(context.bot, uid, sent_msg.message_id, order_code, ORDER_TIMEOUT_SECONDS))

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text(f"{CE_FAIL} Your access to Avengers Shop has been revoked.", parse_mode="HTML")
        return

    context.user_data.clear()

    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, joined_at, is_banned, wallet_balance) VALUES (?, ?, 0, 0.0)", (user_id, int(time.time())))
    conn.commit()
    conn.close()

    if user_id != ADMIN_ID:
        has_joined, missing = await check_user_joined_all(context.bot, user_id)
        if not has_joined:
            join_kb = await get_force_sub_keyboard(context.bot)
            force_msg = (
                f"👋 <b>Welcome to Avengers Shop!</b> {CE_SPARKLE}\n\n"
                f"{CE_RADIO} Unlock store access by joining our official channels:\n"
                f"• <b>Avengers Official Proofs</b>\n"
                f"• <b>AI & Updates Network</b>\n\n"
                f"Tap <b>✅ I've Joined — Verify</b> once done."
            )
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=force_msg,
                    reply_markup=join_kb,
                    message_effect_id=PARTY_POPPER_EFFECT_ID,
                    parse_mode="HTML"
                )
            except Exception:
                await update.message.reply_text(force_msg, reply_markup=join_kb, parse_mode="HTML")
            return

    if context.args and context.args[0] == "buy":
        await buy_coupons(update, context)
        return

    welcome_text = (
        f"{CE_VERIFY} <b>WELCOME TO AVENGERS SHOP</b> {CE_SPARKLE}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>"
        f"• <b>Instant Auto Dispatch:</b> Active 24/7\n"
        f"• <b>Instant Voucher Recovery:</b> Seamless retrieval\n"
        f"• <b>Wallet Fast-Checkout:</b> 1-Click payments\n"
        f"• <b>Live Proofs Channel:</b> Synchronized"
        f"</blockquote>\n\n"
        f"Select an option from the menu below:"
    )

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=welcome_text,
            reply_markup=get_user_keyboard(user_id),
            message_effect_id=PARTY_POPPER_EFFECT_ID,
            parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text(welcome_text, reply_markup=get_user_keyboard(user_id), parse_mode="HTML")

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == ADMIN_ID:
        await context.bot.send_message(
            chat_id=uid,
            text=f"{CE_ADMIN} <b>AVENGERS SHOP CONTROL CONSOLE</b>\nAccess authorized.",
            reply_markup=get_seller_keyboard(),
            message_effect_id=PARTY_POPPER_EFFECT_ID,
            parse_mode="HTML"
        )
    else:
        await update.message.reply_text("⛔ You are not authorized to use this command.")

async def buy_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_user_banned(uid):
        return

    if uid != ADMIN_ID:
        has_joined, missing = await check_user_joined_all(context.bot, uid)
        if not has_joined:
            join_kb = await get_force_sub_keyboard(context.bot)
            await update.message.reply_text(f"{CE_ALERT} Store access locked! Join our channels first:", reply_markup=join_kb, parse_mode="HTML")
            return

    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("""
        SELECT p.id, p.name, p.price, p.flash_price, p.flash_expiry,
               (SELECT COUNT(*) FROM stock WHERE product_id = p.id AND is_sold = 0) as avail
        FROM products p
    """)
    products = c.fetchall()
    conn.close()

    if not products:
        await update.message.reply_text(f"{CE_FAIL} No items currently listed in stock.", parse_mode="HTML")
        return

    now_ts = int(time.time())
    kb = []
    for p in products:
        pid, name, price, flash_price, flash_expiry, avail = p[0], str(p[1]), float(p[2] or 0), float(p[3] or 0), int(p[4] or 0), int(p[5] or 0)
        display_price = f"₹{int(flash_price) if flash_price.is_integer() else flash_price} (FLASH SALE)" if (flash_price > 0 and flash_expiry > now_ts) else f"₹{int(price) if price.is_integer() else price}"

        if avail > 0:
            kb.append([InlineKeyboardButton(f"🟢 {name} — {display_price} ({avail} left)", callback_data=f"userbuy_{pid}")])
        else:
            kb.append([InlineKeyboardButton(f"🔴 {name} — {display_price} (Out of stock)", callback_data=f"alertme_{pid}")])

    kb.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")])

    try:
        await context.bot.send_message(
            chat_id=uid,
            text=f"{CE_SHOP} <b>Select Item to Buy:</b>",
            reply_markup=InlineKeyboardMarkup(kb),
            message_effect_id=PARTY_POPPER_EFFECT_ID,
            parse_mode="HTML"
        )
    except Exception:
        await update.message.reply_text("👇 <b>Select Item to Buy:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

async def process_and_add_stock(raw_content: str, pid: int, update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect("store.db")
    c = conn.cursor()
    c.execute("SELECT name, format_type, price FROM products WHERE id = ?", (pid,))
    p_info = c.fetchone()
    if not p_info:
        conn.close()
        return
    pname, fmt, unit_price = p_info
    is_session = (fmt == "session")

    new_codes = extract_all_json_objects(raw_content)
    if not is_session and not new_codes:
        new_codes = [l.strip() for l in raw_content.split("\n") if l.strip()]

    if not new_codes:
        conn.close()
        await update.message.reply_text(f"{CE_FAIL} File ya message me koi valid JSON/records detect nahi hue.", parse_mode="HTML")
        return

    c.execute("SELECT session_key FROM stock WHERE product_id = ?", (pid,))
    seen_keys = {row[0] for row in c.fetchall() if row[0]}

    added = 0
    for code_str in new_codes:
        s_key = _session_id_of(code_str) if is_session else code_str
        if s_key and s_key in seen_keys:
            continue
        if s_key:
            seen_keys.add(s_key)
        c.execute("INSERT INTO stock (product_id, item_data, session_key) VALUES (?, ?, ?)", (pid, code_str, s_key))
        added += 1

    c.execute("SELECT COUNT(*) FROM stock WHERE product_id = ? AND is_sold = 0", (pid,))
    total_live_stock = c.fetchone()[0]

    c.execute("SELECT user_id FROM restock_alerts WHERE product_id = ?", (pid,))
    alert_users = [row[0] for row in c.fetchall()]
    c.execute("DELETE FROM restock_alerts WHERE product_id = ?", (pid,))
    conn.commit()
    conn.close()

    context.user_data.pop("action", None)
    await update.message.reply_text(
        f"{CE_SUCCESS} <b>{added} items batch-ingested into Avengers Store!</b>\n"
        f"{CE_BOX} <b>Product:</b> {pname}\n"
        f"{CE_CHART} <b>Total Live In Stock:</b> <code>{total_live_stock}</code> units.",
        reply_markup=get_product_manage_kb(pid),
        parse_mode="HTML"
    )

    bot_username = (await context.bot.get_me()).username
    channel_post = (
        f"{CE_ALERT} <b>PRODUCT RESTOCK DROP!</b> {CE_FIRE}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<blockquote>"
        f"{CE_BOX} <b>Item:</b> <code>{pname}</code>\n"
        f"{CE_VERIFY} <b>Added Units:</b> <code>+{added} Fresh</code>\n"
        f"{CE_CHART} <b>Live Available:</b> <code>{total_live_stock} Units</code>\n"
        f"💰 <b>Unit Price:</b> <code>₹{unit_price}</code>"
        f"</blockquote>\n\n"
        f"Instant auto-delivery active. Grab yours now!"
    )
    ch_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛍️ Buy Instantly", url=f"https://t.me/{bot_username}?start=buy")]])
    try:
        await context.bot.send_message(chat_id=PROOF_CHANNEL_ID, text=channel_post, reply_markup=ch_kb, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Restock channel broadcast error: {e}")

    if alert_users:
        dm_text = (
            f"🔔 <b>RESTOCK NOTIFICATION!</b>\n\n"
            f"Aapne jiss item ke liye alert lagaya tha wo stock me aa gaya hai:\n\n"
            f"<blockquote>"
            f"{CE_BOX} <b>Product:</b> <code>{pname}</code>\n"
            f"{CE_CHART} <b>Available:</b> <code>{total_live_stock} Units</code>\n"
            f"💰 <b>Price:</b> <code>₹{unit_price}</code>"
            f"</blockquote>\n\n"
            f"Tap below to order instantly:"
        )
        dm_kb = InlineKeyboardMarkup([[InlineKeyboardButton("🛍️ Buy Now", callback_data=f"userbuy_{pid}")]])
        sent_dm = 0
        for u in alert_users:
            try:
                await context.bot.send_message(chat_id=u, text=dm_text, reply_markup=dm_kb, message_effect_id=PARTY_POPPER_EFFECT_ID, parse_mode="HTML")
                sent_dm += 1
            except Exception:
                pass
        await update.message.reply_text(f"{CE_RADIO} Direct PM alert sent to <code>{sent_dm}</code> interested buyers.", parse_mode="HTML")

async def file_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != ADMIN_ID:
        return

    action = context.user_data.get("action")
    if action == "awaiting_stock":
        doc = update.message.document
        file_obj = await doc.get_file()
        file_bytes = await file_obj.download_as_bytearray()
        try:
            content = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            content = file_bytes.decode("latin-1", errors="ignore")

        pid = context.user_data.get("target_pid")
        await process_and_add_stock(content, pid, update, context)

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    uid = update.effective_user.id

    if is_user_banned(uid):
        await query.answer("🚫 You are banned from this shop.", show_alert=True)
        return

    if data == "verify_force_join":
        has_joined, missing = await check_user_joined_all(context.bot, uid)
        if has_joined:
            await query.answer("🎉 Verification Successful! Access Granted.", show_alert=True)
            try:
                await query.message.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=uid,
                text=f"{CE_VERIFY} <b>Access Unlocked!</b> Ab aap products buy kar sakte hain:",
                reply_markup=get_user_keyboard(uid),
                message_effect_id=PARTY_POPPER_EFFECT_ID,
                parse_mode="HTML"
            )
        else:
            await query.answer("❌ Abhi dono channels join nahi kiye! Dono join karein.", show_alert=True)
        return

    if data == "wallet_add_funds":
        await query.answer()
        context.user_data["action"] = "awaiting_wallet_amount"
        await query.message.reply_text(f"{CE_WALLET} <b>Enter Amount to Add to Wallet:</b>\n<i>(Minimum amount: ₹10)</i>\n\nType amount below (e.g. 50, 100, 250):", parse_mode="HTML")
        return

    if data.startswith("selord_"):
        await query.answer()
        selected_code = data.split("_", 1)[1]
        context.user_data["action"] = "awaiting_dispute_text"
        context.user_data["dispute_order_code"] = selected_code
        try: await query.message.delete()
        except Exception: pass
        await context.bot.send_message(
            chat_id=uid,
            text=f"📝 <b>Order Selected:</b> <code>{selected_code}</code>\n\nApni problem detail me likhein (aur uncut video proof ready rakhein):",
            parse_mode="HTML"
        )
        return

    if data.startswith("alertme_"):
        pid = int(data.split("_")[1])
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        try:
            c.execute("INSERT OR IGNORE INTO restock_alerts (product_id, user_id) VALUES (?, ?)", (pid, uid))
            conn.commit()
            await query.answer("🔔 Alert Registered! Stock aane par direct notification mil jayega.", show_alert=True)
        except Exception:
            await query.answer("Already registered for alert.", show_alert=True)
        conn.close()
        return

    if data.startswith("refreshtime_"):
        order_code = data.split("_")[1]
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT created_at, status FROM orders WHERE order_code = ?", (order_code,))
        row = c.fetchone()
        conn.close()

        if not row:
            await query.answer("Order not found.", show_alert=True)
            return

        created_at, status = row
        if status == "completed":
            await query.answer("✅ This order has already been paid & fulfilled!", show_alert=True)
            return

        elapsed = int(time.time()) - created_at
        remaining = ORDER_TIMEOUT_SECONDS - elapsed

        if remaining <= 0:
            await query.answer("⌛ ORDER EXPIRED! This 5-minute window has closed.", show_alert=True)
            try:
                await query.message.delete()
            except Exception:
                pass
            return

        updated_timer_text = make_timer_button(remaining)
        await query.answer(f"⏱️ Remaining: {remaining // 60}m {remaining % 60}s")

        try:
            old_kb = query.message.reply_markup.inline_keyboard
            new_kb = []
            for row_btn in old_kb:
                new_row = []
                for btn in row_btn:
                    if btn.callback_data and btn.callback_data.startswith("refreshtime_"):
                        new_row.append(InlineKeyboardButton(updated_timer_text, callback_data=f"refreshtime_{order_code}"))
                    else:
                        new_row.append(btn)
                new_kb.append(new_row)
            await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_kb))
        except Exception:
            pass
        return

    if data.startswith("paywallet_"):
        order_code = data.split("_")[1]
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("""
            SELECT o.user_id, o.product_id, o.quantity, o.total_price, o.status, p.name, p.format_type, u.wallet_balance
            FROM orders o JOIN products p ON o.product_id = p.id JOIN users u ON o.user_id = u.user_id 
            WHERE o.order_code = ?
        """, (order_code,))
        row = c.fetchone()

        if not row:
            conn.close()
            await query.answer("Order not found.", show_alert=True)
            return

        o_uid, pid, qty, total_price, status, pname, fmt, balance = row

        if status == "completed":
            conn.close()
            await query.answer("Already fulfilled!", show_alert=True)
            return

        if balance < total_price:
            conn.close()
            await query.answer("❌ Insufficient Wallet Balance! Please add funds.", show_alert=True)
            return

        c.execute("SELECT id, item_data FROM stock WHERE product_id = ? AND is_sold = 0 LIMIT ?", (pid, qty))
        stock_items = c.fetchall()

        if len(stock_items) < qty:
            conn.close()
            await query.answer("🚨 Stock depleted during checkout! Contact admin.", show_alert=True)
            return

        new_balance = round(balance - total_price, 2)
        sold_ids = [item[0] for item in stock_items]
        codes = [item[1] for item in stock_items]
        saved_dump = json.dumps(codes)

        c.execute(f"UPDATE stock SET is_sold = 1 WHERE id IN ({','.join(['?']*len(sold_ids))})", sold_ids)
        c.execute("UPDATE orders SET status = 'completed', delivered_data = ? WHERE order_code = ?", (saved_dump, order_code))
        c.execute("UPDATE users SET wallet_balance = ? WHERE user_id = ?", (new_balance, o_uid))
        conn.commit()
        conn.close()

        await query.answer("⚡ Paid instantly via Wallet!", show_alert=True)
        await deliver_voucher_to_user(o_uid, codes, pname, order_code, fmt, context.bot)
        await check_low_stock(context.bot, pid, pname)
        return

    if data.startswith("userbuy_"):
        await query.answer()
        pid = int(data.split("_")[1])
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM stock WHERE product_id = ? AND is_sold = 0", (pid,))
        avail = c.fetchone()[0]
        c.execute("SELECT name, price, max_buy FROM products WHERE id = ?", (pid,))
        row = c.fetchone()
        if not row:
            conn.close()
            return
        pname, price, max_buy = row
        max_buy = int(max_buy or 10)
        c.execute("SELECT min_qty, unit_price FROM bulk_rates WHERE product_id = ? ORDER BY min_qty ASC", (pid,))
        bulk_rows = c.fetchall()
        conn.close()

        if avail <= 0:
            await query.answer("🚨 Out of stock!", show_alert=True)
            return

        bulk_desc = ""
        if bulk_rows:
            bulk_desc = f"\n{CE_GIFT} <b>Active Bulk Rates:</b>\n"
            for br in bulk_rows:
                bulk_desc += f"• Buy {br[0]}+ at <b>₹{br[1]:.2f}/each</b>\n"

        max_allowed = min(avail, max_buy)
        text = (
            f"{CE_BOX} <b>Selected Product:</b> <code>{pname}</code>\n"
            f"💰 <b>Base Price:</b> <code>₹{price}</code>\n"
            f"{CE_CHART} <b>In Stock:</b> <code>{avail}</code> (Order Limit: {max_allowed})\n"
            f"{bulk_desc}\n"
            f"Select Quantity to Purchase:"
        )
        try:
            await query.edit_message_text(text, reply_markup=get_qty_keyboard_with_bulk(pid, max_allowed, price), parse_mode="HTML")
        except Exception:
            await query.message.reply_text(text, reply_markup=get_qty_keyboard_with_bulk(pid, max_allowed, price), parse_mode="HTML")
        return

    if data.startswith("setqty_"):
        await query.answer()
        parts = data.split("_")
        pid = int(parts[1])
        qty = int(parts[2])
        try:
            await query.message.delete()
        except Exception:
            pass
        await create_and_send_invoice(query, context, uid, pid, qty)
        return

    if data.startswith("customqty_"):
        await query.answer()
        pid = int(data.split("_")[1])
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM stock WHERE product_id = ? AND is_sold = 0", (pid,))
        avail = c.fetchone()[0]
        c.execute("SELECT max_buy FROM products WHERE id = ?", (pid,))
        max_buy = int(c.fetchone()[0] or 10)
        conn.close()

        context.user_data["action"] = "buy_qty"
        context.user_data["buy_pid"] = pid
        context.user_data["max_stock"] = min(avail, max_buy)
        await query.message.reply_text(f"🔢 Enter quantity manually (Max: {min(avail, max_buy)}):")
        return

    if data == "cancel_order":
        await query.answer("Order cancelled.", show_alert=True)
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    if data.startswith("chkpay_"):
        if is_rate_limited(uid):
            await query.answer("⏳ Rate Limit! Please wait 30 seconds before verifying again.", show_alert=True)
            return

        order_code = data.split("_")[1]
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT o.user_id, o.product_id, o.quantity, o.total_price, o.status, o.created_at FROM orders o WHERE o.order_code = ?", (order_code,))
        order = c.fetchone()

        if not order:
            await query.answer("Order not found.", show_alert=True)
            conn.close()
            return

        order_uid, pid, qty, total_price, status, created_at = order
        
        if status == "completed":
            await query.answer("✅ This order has already been fulfilled!", show_alert=True)
            conn.close()
            return

        now_ts = int(time.time())
        if created_at and (now_ts - created_at > ORDER_TIMEOUT_SECONDS):
            c.execute("UPDATE orders SET status = 'expired' WHERE order_code = ?", (order_code,))
            conn.commit()
            conn.close()
            await query.answer("⌛ This order has expired (5-minute limit reached).", show_alert=True)
            try:
                await query.message.delete()
            except Exception:
                pass
            return

        is_paid, reason, paid_val = verify_payment_gateway(order_code, total_price)

        if not is_paid:
            if "AMOUNT_MISMATCH" in reason:
                fraud_msg = (
                    f"🚨 <b>FRAUD ATTEMPT DETECTED</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"<blockquote>"
                    f"👤 <b>User ID:</b> <code>{uid}</code>\n"
                    f"🏷️ <b>Order:</b> <code>{order_code}</code>\n"
                    f"💰 <b>Expected Exact:</b> <code>₹{total_price}</code>\n"
                    f"⚠️ <b>Paid by User:</b> <code>₹{paid_val}</code>"
                    f"</blockquote>\n\n"
                    f"Transaction blocked."
                )
                try:
                    await context.bot.send_message(chat_id=ADMIN_ID, text=fraud_msg, parse_mode="HTML")
                except Exception:
                    pass

                await query.answer(f"🚨 [PAYMENT REJECTED: AMOUNT MISMATCH]\n\nExact Bill: ₹{total_price} | Received: ₹{paid_val}\nTampering detected. Blocked.", show_alert=True)
            else:
                await query.answer(f"❌ Payment not detected yet.\n\nOrder ID: {order_code}\nExact Amount: ₹{total_price}\nPay via UPI and wait 5 seconds before retrying.", show_alert=True)
            conn.close()
            return

        if pid == 0:
            c.execute("UPDATE orders SET status = 'completed' WHERE order_code = ?", (order_code,))
            c.execute("UPDATE users SET wallet_balance = wallet_balance + ? WHERE user_id = ?", (total_price, order_uid))
            c.execute("SELECT wallet_balance FROM users WHERE user_id = ?", (order_uid,))
            updated_bal = c.fetchone()[0]
            conn.commit()
            conn.close()

            await query.answer("✅ Wallet Recharged Successfully!", show_alert=True)
            try:
                await query.message.delete()
            except Exception:
                pass

            await context.bot.send_message(
                chat_id=order_uid,
                text=f"{CE_SUCCESS} <b>WALLET RECHARGE CONFIRMED!</b>\n\n<blockquote>• Added: <code>₹{total_price}</code>\n• New Balance: <code>₹{updated_bal:.2f}</code></blockquote>\n\nAb aap 1-click se products buy kar sakte hain!",
                message_effect_id=PARTY_POPPER_EFFECT_ID,
                parse_mode="HTML"
            )
            return

        c.execute("SELECT name, format_type FROM products WHERE id = ?", (pid,))
        p_info = c.fetchone()
        if not p_info:
            conn.close()
            return
        pname, fmt = p_info

        c.execute("SELECT id, item_data FROM stock WHERE product_id = ? AND is_sold = 0 LIMIT ?", (pid, qty))
        stock_items = c.fetchall()

        if len(stock_items) < qty:
            conn.close()
            await query.message.reply_text("🚨 Critical: Stock depleted during transaction. Contact Support.", parse_mode="HTML")
            return

        sold_ids = [item[0] for item in stock_items]
        codes = [item[1] for item in stock_items]
        saved_dump = json.dumps(codes)

        c.execute(f"UPDATE stock SET is_sold = 1 WHERE id IN ({','.join(['?']*len(sold_ids))})", sold_ids)
        c.execute("UPDATE orders SET status = 'completed', delivered_data = ? WHERE order_code = ?", (saved_dump, order_code))
        conn.commit()
        conn.close()

        await query.answer("🎉 Payment Verified! Delivering codes...", show_alert=True)
        try:
            await query.message.delete()
        except Exception:
            pass

        await deliver_voucher_to_user(order_uid, codes, pname, order_code, fmt, context.bot)

        # PROOF CHANNEL POST
        try:
            uid_str = str(order_uid)
            masked_uid = f"{uid_str[:2]}****{uid_str[-2:]}" if len(uid_str) >= 4 else "Anonymous"
            masked_oid = f"{order_code[:4]}****{order_code[-4:]}" if len(order_code) >= 8 else "PROTECTED"

            proof_text = (
                f"{CE_VERIFY} <b>NEW TRANSACTION VERIFIED & DISPATCHED</b> {CE_SPARKLE}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<blockquote>"
                f"{CE_BOX} <b>Item:</b> <code>{pname}</code>\n"
                f"🔢 <b>Quantity:</b> <code>{qty} Units</code>\n"
                f"💰 <b>Amount Cleared:</b> <code>₹{total_price}</code>\n"
                f"🆔 <b>Order Reference:</b> <code>{masked_oid}</code>\n"
                f"👤 <b>Buyer:</b> <code>{masked_uid}</code>\n"
                f"{CE_VERIFY} <b>Delivery Speed:</b> Instant Auto-Drop"
                f"</blockquote>\n\n"
                f"{BOT_CREDIT_TAG}"
            )
            await context.bot.send_message(chat_id=PROOF_CHANNEL_ID, text=proof_text, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Proof send error: {e}")

        await check_low_stock(context.bot, pid, pname)
        return

    if data.startswith("repsend_"):
        await query.answer()
        parts = data.split("_")
        target_uid = int(parts[1])
        ref_order = parts[2]

        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT product_id FROM orders WHERE order_code = ?", (ref_order,))
        row = c.fetchone()

        if not row:
            conn.close()
            await query.message.reply_text("Order not found.")
            return

        pid = row[0]
        c.execute("SELECT format_type FROM products WHERE id = ?", (pid,))
        fmt = c.fetchone()[0]

        c.execute("SELECT id, item_data FROM stock WHERE product_id = ? AND is_sold = 0 LIMIT 1", (pid,))
        fresh_item = c.fetchone()

        if not fresh_item:
            conn.close()
            await query.message.reply_text(f"{CE_FAIL} Stock is empty! Unable to dispatch replacement.", parse_mode="HTML")
            return

        item_id, item_data = fresh_item
        c.execute("UPDATE stock SET is_sold = 1 WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

        await deliver_voucher_to_user(target_uid, [item_data], "Replacement Voucher", ref_order, fmt, context.bot)
        await query.message.reply_text(f"{CE_SUCCESS} Replacement sent to User <code>{target_uid}</code> for Order <code>{ref_order}</code>.", parse_mode="HTML")
        return

    if data.startswith("cmpreject_"):
        await query.answer()
        parts = data.split("_")
        target_uid = int(parts[1])
        ref_order = parts[2]
        try:
            await context.bot.send_message(
                chat_id=target_uid,
                text=f"{CE_FAIL} <b>Ticket Closed:</b>\nYour dispute regarding Order <code>{ref_order}</code> was rejected (No uncut video proof provided).",
                parse_mode="HTML"
            )
            await query.message.reply_text(f"Ticket rejected for Order <code>{ref_order}</code>.", parse_mode="HTML")
        except Exception as e:
            await query.message.reply_text(f"Error: {e}")
        return

    if data.startswith("adminreply_"):
        await query.answer()
        target_uid = int(data.split("_")[1])
        context.user_data["action"] = "admin_reply_text"
        context.user_data["reply_target_uid"] = target_uid
        await query.message.reply_text(f"💬 Type reply to User <code>{target_uid}</code>:", parse_mode="HTML")
        return

    if data.startswith("freeextract_"):
        await query.answer()
        pid = int(data.split("_")[1])
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT name, format_type FROM products WHERE id = ?", (pid,))
        pname, fmt = c.fetchone()
        c.execute("SELECT id, item_data FROM stock WHERE product_id = ? AND is_sold = 0 LIMIT 1", (pid,))
        item = c.fetchone()

        if not item:
            conn.close()
            await query.message.reply_text(f"{CE_FAIL} <code>{pname}</code> is out of stock.", parse_mode="HTML")
            return

        item_id, item_data = item
        c.execute("UPDATE stock SET is_sold = 1 WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

        await query.answer("🎁 Delivered!", show_alert=True)
        await deliver_voucher_to_user(uid, [item_data], pname, "FREE-DROP", fmt, context.bot)
        return

    if data == "list_prods":
        await query.answer()
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT id, name, price FROM products")
        prods = c.fetchall()
        conn.close()
        keyboard = [[InlineKeyboardButton(f"📦 {p[1]} (₹{p[2]})", callback_data=f"open_{p[0]}")] for p in prods]
        await query.edit_message_text("⚙️ <b>Inventory Control Panel:</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return

    if data.startswith("open_"):
        await query.answer()
        pid = int(data.split("_")[1])
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT name, format_type, price, max_buy FROM products WHERE id = ?", (pid,))
        name, fmt, price, max_buy = c.fetchone()
        c.execute("SELECT COUNT(*) FROM stock WHERE product_id = ? AND is_sold = 0", (pid,))
        avail = c.fetchone()[0]
        c.execute("SELECT min_qty, unit_price FROM bulk_rates WHERE product_id = ? ORDER BY min_qty ASC", (pid,))
        brates = c.fetchall()
        conn.close()

        bulk_info = "\n• <b>Custom Bulk Tiers:</b> None"
        if brates:
            bulk_info = "\n• <b>Custom Bulk Tiers:</b>\n" + "\n".join([f"   - {b[0]}+ units @ ₹{b[1]:.2f}/each" for b in brates])

        text = (
            f"{CE_BOX} <b>Product:</b> <code>{name}</code>\n"
            f"• <b>Type:</b> <code>{fmt.upper()}</code>\n"
            f"• <b>Base Price:</b> <code>₹{price}</code>\n"
            f"• <b>Stock Balance:</b> <code>{avail}</code>\n"
            f"• <b>Order Limit:</b> <code>{max_buy}</code>"
            f"{bulk_info}"
        )
        await query.edit_message_text(text, reply_markup=get_product_manage_kb(pid), parse_mode="HTML")
        return

    if data.startswith("mngbulk_"):
        await query.answer()
        pid = int(data.split("_")[1])
        context.user_data["action"] = "awaiting_bulk_entry"
        context.user_data["bulk_pid"] = pid

        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT min_qty, unit_price FROM bulk_rates WHERE product_id = ? ORDER BY min_qty ASC", (pid,))
        rows = c.fetchall()
        conn.close()

        txt = f"{CE_CHART} <b>BULK RATE MANAGER</b>\n\nCurrent Tiers:\n"
        if not rows:
            txt += "<i>(No custom tiers set yet)</i>\n\n"
        else:
            for r in rows:
                txt += f"• Min Qty <code>{r[0]}</code>: ₹<code>{r[1]:.2f}</code> per piece\n"
            txt += "\n"

        txt += "Reply in format: <code>&lt;min_qty&gt;:&lt;unit_price&gt;</code> (e.g. <code>5:8</code>) or send <code>clear</code>."
        await query.message.reply_text(txt, parse_mode="HTML")
        return

    if data.startswith("startflash_"):
        await query.answer()
        pid = int(data.split("_")[1])
        context.user_data["action"] = "awaiting_flash_details"
        context.user_data["flash_pid"] = pid
        await query.message.reply_text(f"{CE_FIRE} Reply in format: <code>&lt;price&gt;:&lt;duration_in_hours&gt;</code> (e.g. <code>15:2</code>) or send <code>stop</code>.", parse_mode="HTML")
        return

    if data.startswith("edprice_"):
        await query.answer()
        pid = int(data.split("_")[1])
        context.user_data["action"] = "ed_price"
        context.user_data["target_pid"] = pid
        await query.message.reply_text("💰 Enter new base price:")
        return

    if data.startswith("edname_"):
        await query.answer()
        pid = int(data.split("_")[1])
        context.user_data["action"] = "ed_name"
        context.user_data["target_pid"] = pid
        await query.message.reply_text("✏️ Enter new name:")
        return

    if data.startswith("edmax_"):
        await query.answer()
        pid = int(data.split("_")[1])
        context.user_data["action"] = "ed_max"
        context.user_data["target_pid"] = pid
        await query.message.reply_text("🔢 Enter max buy limit:")
        return

    if data.startswith("addstk_"):
        await query.answer()
        pid = int(data.split("_")[1])
        context.user_data["action"] = "awaiting_stock"
        context.user_data["target_pid"] = pid
        await query.message.reply_text(f"{CE_KEY} <b>Stock bhejein:</b>\n\n• Text/JSON direct message me paste karein\n• YA <code>.json</code> / <code>.txt</code> file upload karein.", parse_mode="HTML")
        return

    if data.startswith("delprod_"):
        await query.answer()
        pid = int(data.split("_")[1])
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE id = ?", (pid,))
        c.execute("DELETE FROM stock WHERE product_id = ?", (pid,))
        c.execute("DELETE FROM bulk_rates WHERE product_id = ?", (pid,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"{CE_FAIL} Product removed.", parse_mode="HTML")
        return

    if data.startswith("fmt_"):
        await query.answer()
        context.user_data["new_fmt"] = "session" if data == "fmt_session" else "text"
        context.user_data["action"] = "add_prod_price"
        await query.edit_message_text("💰 Enter base unit price (₹):")
        return

# --- TEXT ROUTER ---
async def text_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    uid = update.effective_user.id

    if is_user_banned(uid):
        return

    action = context.user_data.get("action")

    if text in ["🛍️ Buy Vouchers", "Buy Vouchers", "🛒 Buy Products"]:
        await buy_coupons(update, context)
        return

    if text in ["📦 My Orders", "My Orders"]:
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("""
            SELECT o.order_code, p.name, o.quantity, o.total_price, o.status 
            FROM orders o JOIN products p ON o.product_id = p.id 
            WHERE o.user_id = ? ORDER BY o.id DESC LIMIT 5
        """, (uid,))
        rows = c.fetchall()
        conn.close()
        msg = f"{CE_BOX} <b>YOUR RECENT TRANSACTIONS:</b>\n\n<blockquote>"
        for code, name, qty, amt, status in rows:
            msg += f"• <code>{code}</code>: {name} (x{qty}) - ₹{amt} [{status.upper()}]\n"
        msg += "</blockquote>"
        await update.message.reply_text(msg if rows else "No orders recorded yet.", parse_mode="HTML")
        return

    if text in ["💳 My Wallet", "My Wallet"]:
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT wallet_balance FROM users WHERE user_id = ?", (uid,))
        row = c.fetchone()
        balance = float(row[0]) if row and row[0] else 0.0
        conn.close()

        w_msg = (
            f"{CE_WALLET} <b>YOUR WALLET BALANCE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"👤 <b>User ID:</b> <code>{uid}</code>\n"
            f"💳 <b>Available Funds:</b> <code>₹{balance:.2f}</code>"
            f"</blockquote>\n\n"
            f"⚡ Wallet balance se aap 1-click me instantly voucher khareed sakte hain."
        )
        wallet_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Funds to Wallet", callback_data="wallet_add_funds")]
        ])
        await update.message.reply_text(w_msg, reply_markup=wallet_kb, parse_mode="HTML")
        return

    if action == "awaiting_wallet_amount":
        try:
            amount = float(text)
            if amount < 10:
                await update.message.reply_text(f"{CE_ALERT} Minimum recharge amount is <b>₹10</b>. Please enter 10 or more:", parse_mode="HTML")
                return
        except ValueError:
            await update.message.reply_text("⚠️ Please enter a valid numeric amount:")
            return

        context.user_data.clear()
        await create_wallet_recharge_invoice(update.message, context, uid, amount)
        return

    if text in ["🔍 Recover Voucher", "Recover Voucher"]:
        context.user_data["action"] = "awaiting_recovery_code"
        await update.message.reply_text(
            f"{CE_SEARCH} <b>VOUCHER RECOVERY SYSTEM</b>\n\nEnter your <b>Order Reference</b> (e.g. <code>AVG-1723...</code>):",
            parse_mode="HTML"
        )
        return

    if action == "awaiting_recovery_code":
        context.user_data.clear()
        target_code = text.strip()
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("""
            SELECT o.delivered_data, p.name, p.format_type 
            FROM orders o JOIN products p ON o.product_id = p.id 
            WHERE o.order_code = ? AND o.user_id = ? AND o.status = 'completed'
        """, (target_code, uid))
        row = c.fetchone()
        conn.close()

        if not row or not row[0]:
            await update.message.reply_text(f"{CE_FAIL} No completed order found with this code on your account.", parse_mode="HTML")
            return

        codes = json.loads(row[0])
        await update.message.reply_text(f"{CE_SEARCH} <b>Voucher Found! Re-delivering to chat:</b>", parse_mode="HTML")
        await deliver_voucher_to_user(uid, codes, row[1], target_code, row[2], context.bot)
        return

    if text in ["🎫 Support", "Support"]:
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("""
            SELECT o.order_code, p.name 
            FROM orders o JOIN products p ON o.product_id = p.id 
            WHERE o.user_id = ? AND o.status = 'completed' 
            ORDER BY o.id DESC LIMIT 5
        """, (uid,))
        completed_orders = c.fetchall()
        conn.close()

        if not completed_orders:
            await update.message.reply_text(
                f"{CE_FAIL} <b>No Completed Orders Found</b>\n\n"
                "Aapke account par koi bhi successfully completed order nahi mila.\n"
                "Support dispute sirf verified completed orders ke liye open ho sakta hai.",
                parse_mode="HTML"
            )
            return

        kb = []
        for o_code, p_name in completed_orders:
            kb.append([InlineKeyboardButton(f"📦 {p_name} ({o_code})", callback_data=f"selord_{o_code}")])
        kb.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")])

        await update.message.reply_text(
            f"{CE_SUPPORT} <b>Support Desk — Select Completed Order</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Kripya jis order ke sath issue hai use niche select karein:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML"
        )
        return

    if text in ["📖 How to Use", "How to Use"]:
        guide_text = (
            f"{CE_GUIDE} <b>HOW TO USE & REDEEM</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"1. Tap <b>🛍️ Buy Vouchers</b> and select item.\n"
            f"2. Pay exact amount shown on QR within 5 minutes.\n"
            f"3. After payment, tap <b>✅ I Have Paid</b>.\n"
            f"4. Voucher code deliver ho jayega.\n"
            f"</blockquote>\n\n"
            f"{CE_ALERT} <b>NOTICE:</b> Mandatory uncut video proof required for disputes!"
        )
        await update.message.reply_text(guide_text, parse_mode="HTML")
        return

    if action == "awaiting_dispute_text":
        selected_code = context.user_data.get("dispute_order_code", "UNKNOWN")
        context.user_data.clear()
        user = update.effective_user
        username = f"@{user.username}" if user.username else "No Username"
        first_name = user.first_name or "Customer"
        direct_dm_url = f"https://t.me/{user.username}" if user.username else f"tg://user?id={uid}"

        admin_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"💬 DM ({first_name})", url=direct_dm_url)],
            [InlineKeyboardButton("🔄 1-Click Replace", callback_data=f"repsend_{uid}_{selected_code}"), InlineKeyboardButton("❌ Reject", callback_data=f"cmpreject_{uid}_{selected_code}")],
            [InlineKeyboardButton("📨 Reply via Bot", callback_data=f"adminreply_{uid}")]
        ])

        admin_notice = (
            f"{CE_ALERT} <b>NEW VERIFIED CUSTOMER TICKET</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"👤 <b>Customer:</b> <a href=\"tg://user?id={uid}\">{first_name}</a>\n"
            f"🔗 <b>Username:</b> {username}\n"
            f"🆔 <b>Telegram ID:</b> <code>{uid}</code>\n"
            f"📦 <b>Order ID:</b> <code>{selected_code}</code>\n\n"
            f"💬 <b>Message:</b>\n\"{text}\""
            f"</blockquote>"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_notice, reply_markup=admin_markup, parse_mode="HTML")
            await update.message.reply_text(f"{CE_SUCCESS} Aapki query submit ho chuki hai! Support desk review karega.", parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ticket submit error: {e}")
            await update.message.reply_text("Submission failed.")
        return

    if action == "admin_reply_text" and uid == ADMIN_ID:
        target_uid = context.user_data.get("reply_target_uid")
        context.user_data.clear()
        try:
            user_msg = (
                f"{CE_SUPPORT} <b>Support Desk Response:</b>\n\n"
                f"<blockquote>{text}</blockquote>\n\n"
                f"🔒 <i>Ye ticket close ho gaya hai. Direct reply disabled hai. Nayi help ke liye menu me 🎫 Support use karein.</i>"
            )
            await context.bot.send_message(chat_id=target_uid, text=user_msg, parse_mode="HTML")
            await update.message.reply_text(f"{CE_SUCCESS} Reply delivered to User <code>{target_uid}</code> and ticket closed.", parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"Delivery failed: {e}")
        return

    if uid != ADMIN_ID and not action:
        await update.message.reply_text(
            "🔒 <b>Direct Replies Disabled</b>\n\n"
            "Aap direct text message nahi bhej sakte.\n"
            "Support lene ke liye menu me <b>🎫 Support</b> par tap karke apna order select karein.",
            reply_markup=get_user_keyboard(uid),
            parse_mode="HTML"
        )
        return

    if text in ["👑 Admin Console", "SELLER DASHBOARD"] and uid == ADMIN_ID:
        await context.bot.send_message(
            chat_id=uid,
            text=f"{CE_ADMIN} <b>AVENGERS CONTROL CONSOLE</b>",
            reply_markup=get_seller_keyboard(),
            message_effect_id=PARTY_POPPER_EFFECT_ID,
            parse_mode="HTML"
        )
        return

    if text in ["🔙 Exit to Home", "Shop Home"]:
        context.user_data.clear()
        await update.message.reply_text("🏠 <b>Avengers Main Desk</b>", reply_markup=get_user_keyboard(uid), parse_mode="HTML")
        return

    if text in ["🔥 Flash Sale"] and uid == ADMIN_ID:
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT id, name, price FROM products")
        prods = c.fetchall()
        conn.close()
        if not prods:
            await update.message.reply_text("No products listed.")
            return
        kb = [[InlineKeyboardButton(f"🔥 {p[1]}", callback_data=f"startflash_{p[0]}")] for p in prods]
        await update.message.reply_text(f"{CE_FIRE} <b>Select Product for Flash Sale:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    if action == "awaiting_flash_details" and uid == ADMIN_ID:
        pid = context.user_data.get("flash_pid")
        context.user_data.clear()
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        if text.lower() == "stop":
            c.execute("UPDATE products SET flash_price = 0, flash_expiry = 0 WHERE id = ?", (pid,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"{CE_SUCCESS} Flash sale cancelled.", parse_mode="HTML")
            return

        if ":" in text:
            parts = text.split(":")
            try:
                f_price = float(parts[0].strip())
                f_hours = float(parts[1].strip())
                expiry_ts = int(time.time() + (f_hours * 3600))
                c.execute("UPDATE products SET flash_price = ?, flash_expiry = ? WHERE id = ?", (f_price, expiry_ts, pid))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"{CE_FIRE} Flash sale live at ₹{f_price} for {f_hours} hours!", parse_mode="HTML")
                return
            except ValueError:
                pass
        conn.close()
        await update.message.reply_text("⚠️ Format: `<price>:<hours>` (e.g. `15:2`) or `stop`.")
        return

    if action == "awaiting_bulk_entry" and uid == ADMIN_ID:
        pid = context.user_data.get("bulk_pid")
        context.user_data.clear()
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        if text.lower() == "clear":
            c.execute("DELETE FROM bulk_rates WHERE product_id = ?", (pid,))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"{CE_SUCCESS} All bulk tiers cleared.", reply_markup=get_product_manage_kb(pid), parse_mode="HTML")
            return

        if ":" in text:
            parts = text.split(":")
            try:
                min_q = int(parts[0].strip())
                u_pr = float(parts[1].strip())
                c.execute("""
                    INSERT INTO bulk_rates (product_id, min_qty, unit_price)
                    VALUES (?, ?, ?)
                    ON CONFLICT(product_id, min_qty) DO UPDATE SET unit_price = excluded.unit_price
                """, (pid, min_q, u_pr))
                conn.commit()
                conn.close()
                await update.message.reply_text(f"{CE_SUCCESS} Bulk Tier: <b>{min_q}+ items @ ₹{u_pr:.2f}/pc</b>", reply_markup=get_product_manage_kb(pid), parse_mode="HTML")
                return
            except ValueError:
                pass
        conn.close()
        await update.message.reply_text("⚠️ Format: `<min_qty>:<unit_price>` (e.g. `5:8`) or `clear`.")
        return

    if text in ["🚫 Ban / Unban User"] and uid == ADMIN_ID:
        context.user_data["action"] = "awaiting_ban_uid"
        await update.message.reply_text("🚫 Enter Target Telegram User ID:")
        return

    if action == "awaiting_ban_uid" and uid == ADMIN_ID:
        context.user_data.clear()
        try:
            target = int(text)
            conn = sqlite3.connect("store.db")
            c = conn.cursor()
            c.execute("SELECT is_banned FROM users WHERE user_id = ?", (target,))
            row = c.fetchone()
            new_state = 1 if (not row or row[0] == 0) else 0
            if not row:
                c.execute("INSERT INTO users (user_id, joined_at, is_banned) VALUES (?, ?, 1)", (target, int(time.time())))
            else:
                c.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_state, target))
            conn.commit()
            conn.close()
            await update.message.reply_text(f"User <code>{target}</code> status: {'BANNED 🚫' if new_state == 1 else 'UNBANNED ✅'}", parse_mode="HTML")
        except ValueError:
            await update.message.reply_text("⚠️ Enter numeric User ID.")
        return

    if text in ["🔄 Replace By Order ID"] and uid == ADMIN_ID:
        context.user_data["action"] = "awaiting_replace_order_id"
        await update.message.reply_text("🔄 Enter Order ID (e.g., `AVG-1723...`):")
        return

    if action == "awaiting_replace_order_id" and uid == ADMIN_ID:
        code = text.strip()
        context.user_data.clear()
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT user_id, product_id FROM orders WHERE order_code = ?", (code,))
        row = c.fetchone()
        if not row:
            conn.close()
            await update.message.reply_text(f"{CE_FAIL} Order ID not found.", parse_mode="HTML")
            return

        target_uid, pid = row
        c.execute("SELECT format_type FROM products WHERE id = ?", (pid,))
        fmt = c.fetchone()[0]

        c.execute("SELECT id, item_data FROM stock WHERE product_id = ? AND is_sold = 0 LIMIT 1", (pid,))
        fresh_item = c.fetchone()
        if not fresh_item:
            conn.close()
            await update.message.reply_text(f"{CE_ALERT} Out of stock!", parse_mode="HTML")
            return

        item_id, item_data = fresh_item
        c.execute("UPDATE stock SET is_sold = 1 WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

        await deliver_voucher_to_user(target_uid, [item_data], "Manual Order Replacement", code, fmt, context.bot)
        await update.message.reply_text(f"{CE_SUCCESS} Replacement sent to User <code>{target_uid}</code>.", parse_mode="HTML")
        return

    if text in ["📊 Sales Dashboard"] and uid == ADMIN_ID:
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(*), SUM(total_price) FROM orders WHERE status = 'completed'")
        row = c.fetchone()
        completed_orders, total_revenue = row[0] or 0, round(row[1] or 0.0, 2)
        c.execute("SELECT COUNT(*) FROM stock WHERE is_sold = 0")
        live_stock = c.fetchone()[0]
        conn.close()

        stats_msg = (
            f"{CE_CHART} <b>AVENGERS ENTERPRISE ANALYTICS</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<blockquote>"
            f"👥 Registered Buyers: <code>{total_users}</code>\n"
            f"💰 Cleared Revenue: <code>₹{total_revenue}</code>\n"
            f"{CE_BOX} Vouchers Delivered: <code>{completed_orders}</code>\n"
            f"🎟️ Live Stock Remaining: <code>{live_stock}</code> units\n"
            f"{CE_RADIO} Proof Channel: <code>{PROOF_CHANNEL_ID}</code>"
            f"</blockquote>"
        )
        await update.message.reply_text(stats_msg, parse_mode="HTML")
        return

    if text in ["📢 Mass Broadcast"] and uid == ADMIN_ID:
        context.user_data["action"] = "awaiting_broadcast"
        await update.message.reply_text("📢 Enter broadcast text:")
        return

    if action == "awaiting_broadcast" and uid == ADMIN_ID:
        context.user_data.clear()
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE is_banned = 0")
        all_users = c.fetchall()
        conn.close()

        sent = 0
        for u in all_users:
            try:
                await context.bot.send_message(chat_id=u[0], text=f"{CE_RADIO} <b>AVENGERS STORE UPDATE:</b>\n\n<blockquote>{text}</blockquote>", parse_mode="HTML")
                sent += 1
            except Exception:
                pass
        await update.message.reply_text(f"{CE_SUCCESS} Broadcast sent to <code>{sent}</code> users.", parse_mode="HTML")
        return

    if text in ["🧹 Purge Sold Stock"] and uid == ADMIN_ID:
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("DELETE FROM stock WHERE is_sold = 1")
        conn.commit()
        conn.close()
        await update.message.reply_text("🧹 Purged sold records.")
        return

    if text in ["📦 Stock Manager"] and uid == ADMIN_ID:
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT id, name, price FROM products")
        prods = c.fetchall()
        conn.close()
        kb = [[InlineKeyboardButton(f"📦 {p[1]} (₹{p[2]})", callback_data=f"open_{p[0]}")] for p in prods]
        await update.message.reply_text("⚙️ <b>Select Product:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        return

    if text in ["➕ Add Product"] and uid == ADMIN_ID:
        context.user_data["action"] = "add_prod_name"
        await update.message.reply_text("Enter product title:")
        return

    if text in ["🎁 Free Code"] and uid == ADMIN_ID:
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("SELECT id, name FROM products")
        prods = c.fetchall()
        conn.close()
        kb = [[InlineKeyboardButton(f"🎁 Free: {p[1]}", callback_data=f"freeextract_{p[0]}")] for p in prods]
        await update.message.reply_text("Extract without payment:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if action == "awaiting_stock":
        pid = context.user_data.get("target_pid")
        await process_and_add_stock(text, pid, update, context)
        return

    if action == "ed_price":
        pid = context.user_data["target_pid"]
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("UPDATE products SET price = ? WHERE id = ?", (float(text), pid))
        conn.commit()
        conn.close()
        context.user_data.clear()
        await update.message.reply_text(f"{CE_SUCCESS} Price updated.", reply_markup=get_product_manage_kb(pid), parse_mode="HTML")
        return

    if action == "ed_name":
        pid = context.user_data["target_pid"]
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("UPDATE products SET name = ? WHERE id = ?", (text, pid))
        conn.commit()
        conn.close()
        context.user_data.clear()
        await update.message.reply_text(f"{CE_SUCCESS} Title updated.", reply_markup=get_product_manage_kb(pid), parse_mode="HTML")
        return

    if action == "ed_max":
        pid = context.user_data["target_pid"]
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("UPDATE products SET max_buy = ? WHERE id = ?", (int(text), pid))
        conn.commit()
        conn.close()
        context.user_data.clear()
        await update.message.reply_text(f"{CE_SUCCESS} Limit updated.", reply_markup=get_product_manage_kb(pid), parse_mode="HTML")
        return

    if action == "add_prod_name":
        context.user_data["new_name"] = text
        kb = [[InlineKeyboardButton("Session Accounts", callback_data="fmt_session")], [InlineKeyboardButton("Plain Text Vouchers", callback_data="fmt_text")]]
        context.user_data.pop("action", None)
        await update.message.reply_text("Choose item structure:", reply_markup=InlineKeyboardMarkup(kb))
        return

    if action == "add_prod_price":
        context.user_data["new_price"] = float(text)
        context.user_data["action"] = "add_prod_maxbuy"
        await update.message.reply_text("Enter max buy quantity per order:")
        return

    if action == "add_prod_maxbuy":
        max_buy = int(text)
        conn = sqlite3.connect("store.db")
        c = conn.cursor()
        c.execute("INSERT INTO products (name, format_type, price, max_buy) VALUES (?, ?, ?, ?)",
                  (context.user_data["new_name"], context.user_data["new_fmt"], context.user_data["new_price"], max_buy))
        conn.commit()
        conn.close()
        context.user_data.clear()
        await update.message.reply_text(f"{CE_SUCCESS} Product added to catalog.", reply_markup=get_seller_keyboard(), parse_mode="HTML")
        return

    if action == "buy_qty":
        try:
            qty = int(text)
            if qty <= 0: raise ValueError
        except ValueError:
            await update.message.reply_text("⚠️ Enter positive number:")
            return
        if qty > context.user_data.get("max_stock", 1):
            await update.message.reply_text(f"⚠️ Limit is {context.user_data.get('max_stock', 1)}.")
            return
        await create_and_send_invoice(update.message, context, uid, context.user_data["buy_pid"], qty)
        return

# --- POST INIT ---
async def post_init(application: Application):
    asyncio.create_task(hourly_stock_broadcast_loop(application.bot))

# --- MAIN ENGINE ---
def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_router))
    app.add_handler(MessageHandler(filters.Document.ALL, file_message_router))

    print("⚡ Avengers Shop Live...")
    app.run_polling()

if __name__ == "__main__":
    main()
