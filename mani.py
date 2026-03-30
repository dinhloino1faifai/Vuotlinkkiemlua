import telebot
import requests
import json
import os
import threading
from telebot import types

# --- CẤU HÌNH HỆ THỐNG ---
API_TOKEN = '8746785738:AAEVb7zeolI0bhfNfHp0F3K3j05oZEb3nt8'
ADMIN_ID = 6949569713
DB_FILE = "dinhloi_database.json"

bot = telebot.TeleBot(API_TOKEN, threaded=True, num_threads=10)

# --- QUẢN LÝ DỮ LIỆU ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "users": {}, 
        "banned": [],
        "config": {
            "price_task": 400, 
            "price_ref": 100, 
            "min_withdraw": 10000,
            "target_url": "https://t.me/DinhLoiStore",
            "api_key": "67bc6098f0489214f14e5659"
        }
    }

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- HÀM TRỢ GIÚP ---
def get_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎯 Làm nhiệm vụ", "💰 Tài khoản")
    markup.add("🏆 Bảng xếp hạng", "👫 Mời bạn bè")
    markup.add("💳 Rút tiền", "📞 Hỗ trợ")
    return markup

# --- XỬ LÝ LỆNH START (SMART LOGIC) ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    uid = str(message.from_user.id)
    args = message.text.split()
    conf = db["config"]
    
    # 1. Kiểm tra nếu quay lại để xác nhận nhiệm vụ
    if len(args) > 1 and args[1] == "done":
        if uid in db["users"]:
            db["users"][uid]["balance"] += conf["price_task"]
            db["users"][uid]["completed"] += 1
            save_db(db)
            bot.send_message(message.chat.id, f"🎉 **Chúc mừng!**\nBạn đã hoàn thành nhiệm vụ và nhận được **+{conf['price_task']}đ** vào tài khoản.")
            bot.send_message(ADMIN_ID, f"✅ **NHIỆM VỤ XONG!**\n👤: {message.from_user.first_name}\n🆔: `{uid}`\n💰 +{conf['price_task']}đ")
            return

    # 2. Xử lý người dùng mới / Referral
    if uid not in db["users"]:
        ref_by = args[1] if len(args) > 1 and args[1].isdigit() else None
        db["users"][uid] = {
            "name": message.from_user.first_name,
            "balance": 0, "completed": 0, "refs": 0
        }
        
        if ref_by and ref_by in db["users"] and ref_by != uid:
            db["users"][ref_by]["balance"] += conf["price_ref"]
            db["users"][ref_by]["refs"] += 1
            try: bot.send_message(ref_by, f"🎊 Bạn nhận được **+{conf['price_ref']}đ** vì đã mời {message.from_user.first_name}!")
            except: pass
            
        save_db(db)
        bot.send_message(ADMIN_ID, f"🆕 **NGƯỜI DÙNG MỚI**\n👤: {message.from_user.first_name}\n🆔: `{uid}`\n🔗 Ref: {ref_by}")

    bot.send_message(message.chat.id, f"👋 Chào mừng **{message.from_user.first_name}** đến với @Kiemtienngay10m_bot!\n\n🚀 Hãy chọn chức năng bên dưới để bắt đầu kiếm tiền.", reply_markup=get_markup(), parse_mode="Markdown")

# --- LÀM NHIỆM VỤ (AUTO-REDIRECT) ---
@bot.message_handler(func=lambda m: m.text == "🎯 Làm nhiệm vụ")
def handle_task(message):
    if message.from_user.id in db.get("banned", []): return
    
    conf = db["config"]
    bot_name = (bot.get_me()).username
    # Link đích dẫn quay lại bot để cộng tiền
    callback_url = f"https://t.me/{bot_name}?start=done"
    
    api_url = f"https://link4m.co/api-shorten/v2?api={conf['api_key']}&url={callback_url}"
    
    try:
        res = requests.get(api_url).json()
        if res.get('status') == 'success':
            short_url = res.get('shortenedUrl')
            msg = (f"🎯 **NHIỆM VỤ KIẾM TIỀN**\n\n"
                   f"💰 Phần thưởng: **{conf['price_task']}đ**\n"
                   f"👇 Nhấn nút bên dưới để vượt link. Sau khi vượt xong, tiền sẽ tự động được cộng!")
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔗 BẮT ĐẦU VƯỢT LINK", url=short_url))
            bot.send_message(message.chat.id, msg, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Lỗi hệ thống: " + res.get('message'))
    except:
        bot.reply_to(message, "⚠️ Máy chủ Link4M không phản hồi.")

# --- TÀI KHOẢN & RÚT TIỀN ---
@bot.message_handler(func=lambda m: m.text == "💰 Tài khoản")
def handle_account(message):
    u = db["users"].get(str(message.from_user.id))
    text = (f"👤 **Tên:** {u['name']}\n"
            f"🆔 **ID:** `{message.from_user.id}`\n"
            f"💵 **Số dư:** `{u['balance']}đ`\n"
            f"✅ **Đã xong:** {u['completed']} nhiệm vụ\n"
            f"👫 **Bạn bè:** {u['refs']} người")
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🏆 Bảng xếp hạng")
def handle_rank(message):
    top = sorted(db["users"].items(), key=lambda x: x[1]['balance'], reverse=True)[:10]
    txt = "🏆 **TOP 10 NGƯỜI DÙNG XUẤT SẮC**\n\n"
    for i, (uid, info) in enumerate(top, 1):
        txt += f"{i}. {info['name']} — `{info['balance']}đ`\n"
    bot.send_message(message.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👫 Mời bạn bè")
def handle_invite(message):
    bot_name = (bot.get_me()).username
    link = f"https://t.me/{bot_name}?start={message.from_user.id}"
    bot.send_message(message.chat.id, f"👫 **MỜI BẠN BÈ**\n\nNhận ngay **{db['config']['price_ref']}đ** cho mỗi người bạn mời thành công!\n\n🔗 Link giới thiệu của bạn:\n`{link}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💳 Rút tiền")
def handle_withdraw(message):
    u = db["users"].get(str(message.from_user.id))
    if u['balance'] < db['config']['min_withdraw']:
        bot.reply_to(message, f"❌ Bạn cần tối thiểu **{db['config']['min_withdraw']}đ** để rút tiền.")
        return
    msg = bot.reply_to(message, "📩 Nhập: **Số tiền - Ngân hàng - STK - Tên**")
    bot.register_next_step_handler(msg, process_withdraw)

def process_withdraw(message):
    bot.send_message(ADMIN_ID, f"💳 **YÊU CẦU RÚT TIỀN**\n👤: {message.from_user.first_name}\n📝: {message.text}")
    bot.reply_to(message, "✅ Đã gửi yêu cầu rút tiền cho Admin.")

# --- QUẢN LÝ ADMIN (COMMANDS) ---
@bot.message_handler(commands=['gia_task', 'gia_ref', 'set_link', 'thongbao'])
def admin_commands(message):
    if message.from_user.id != ADMIN_ID: return
    cmd = message.text.split()[0]
    try:
        if cmd == "/gia_task":
            db["config"]["price_task"] = int(message.text.split()[1])
            save_db(db)
            bot.reply_to(message, f"✅ Giá nhiệm vụ: {db['config']['price_task']}đ")
        elif cmd == "/gia_ref":
            db["config"]["price_ref"] = int(message.text.split()[1])
            save_db(db)
            bot.reply_to(message, f"✅ Giá mời bạn: {db['config']['price_ref']}đ")
        elif cmd == "/thongbao":
            text = message.text.split(None, 1)[1]
            for uid in db["users"]:
                try: bot.send_message(uid, f"📢 **THÔNG BÁO ADMIN**\n\n{text}", parse_mode="Markdown")
                except: pass
            bot.reply_to(message, "✅ Đã gửi thông báo toàn hệ thống.")
    except: bot.reply_to(message, "⚠️ Sai cú pháp!")

print("Bot @Kiemtienngay10m_bot ULTIMATE is starting...")
bot.infinity_polling()
