import os
import random
import string
import telebot
from telebot import types
import database as db
import railway_api

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))  # آیدی عددی شما

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
db.init_db()

# ذخیره وضعیت موقت کاربران
user_states = {}

def is_admin(user_id):
    return user_id == ADMIN_ID

def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🚀 ساخت پنل جدید"),
        types.KeyboardButton("📋 پنل‌های من")
    )
    markup.add(
        types.KeyboardButton("🔑 تنظیم توکن ریلوی"),
        types.KeyboardButton("ℹ️ راهنما")
    )
    if is_admin(user_id):
        markup.add(types.KeyboardButton("👑 پنل مدیریت"))
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    
    db.save_user(user_id, username, first_name)
    user = db.get_user(user_id)

    welcome_text = (
        f"سلام <b>{first_name}</b> عزیز! 👋\n\n"
        "به ربات خودکارساز دیپلوی پنل Xray روی <b>Railway</b> خوش آمدید.\n\n"
    )

    if not user.get("railway_token"):
        welcome_text += (
            "⚠️ <b>توکن Railway شما ثبت نشده است!</b>\n"
            "برای شروع، لطفاً دکمه «🔑 تنظیم توکن ریلوی» را بزنید و توکن API خود را ارسال کنید."
        )
    else:
        welcome_text += "✅ توکن Railway شما فعال است. می‌توانید با یک کلیک پنل جدید بسازید."

    bot.send_message(user_id, welcome_text, reply_markup=main_keyboard(user_id))

@bot.message_handler(func=lambda msg: msg.text == "🔑 تنظیم توکن ریلوی")
def ask_for_token(message):
    user_id = message.from_user.id
    user_states[user_id] = "WAITING_FOR_TOKEN"
    text = (
        "🔑 <b>نحوه دریافت توکن Railway:</b>\n\n"
        "۱. وارد سایت <a href='https://railway.app/account/tokens'>railway.app/account/tokens</a> شوید.\n"
        "۲. روی دکمه <b>Create Token</b> کلیک کنید.\n"
        "۳. توکن دریافتی را کپی کرده و در پاسخ به همین پیام ارسال کنید."
    )
    bot.send_message(user_id, text, disable_web_page_preview=True)

@bot.message_handler(func=lambda msg: msg.text == "ℹ️ راهنما")
def handle_help(message):
    user_id = message.from_user.id
    default_repo = db.get_setting("default_repo", "hdzirxluci-hub/pablo-panel")
    text = (
        "📖 <b>راهنمای استفاده:</b>\n\n"
        "• این ربات پنل شما را به صورت خودکار از ریپازیتوری زیر روی اکانت ریلوی شما می‌سازد:\n"
        f"<code>{default_repo}</code>\n\n"
        "• پس از اتمام ساخت، دامنه به شما داده می‌شود.\n"
        "• ساخت پنل معمولاً ۱ تا ۳ دقیقه در ریلوی زمان می‌برد تا لود شود."
    )
    bot.send_message(user_id, text)

@bot.message_handler(func=lambda msg: msg.text == "🚀 ساخت پنل جدید")
def start_create_panel(message):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if not user or not user.get("railway_token"):
        bot.send_message(user_id, "❌ ابتدا توکن Railway خود را ثبت کنید.", reply_markup=main_keyboard(user_id))
        return

    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    default_name = f"pablo-panel-{rand_suffix}"

    user_states[user_id] = {"state": "CREATING_PANEL", "name": default_name}

    wait_msg = bot.send_message(
        user_id,
        "⏳ <b>در حال ساخت پروژه روی Railway و اتصال به ریپازیتوری...</b>\nلطفاً چند لحظه شکیبا باشید."
    )

    try:
        repo = db.get_setting("default_repo", "hdzirxluci-hub/pablo-panel")
        result = railway_api.deploy_panel_flow(user["railway_token"], default_name, repo)

        domain = result["domain"]
        db.add_panel(user_id, result["project_id"], result["project_name"], domain, result["repo"])

        domain_link = f"https://{domain}" if domain and not domain.startswith("در حال") else "در حال راه‌اندازی (۱ دقیقه دیگر مجدد چک کنید)"

        success_text = (
            "🎉 <b>پنل شما با موفقیت ساخته شد!</b>\n\n"
            f"📦 <b>نام پروژه:</b> <code>{result['project_name']}</code>\n"
            f"🔗 <b>ریپازیتوری:</b> <code>{result['repo']}</code>\n"
            f"🌐 <b>آدرس پنل:</b> {domain_link}\n\n"
            "⚠️ <i>نکته: حدود ۱ تا ۲ دقیقه طول می‌کشد تا ریلوی پروژه را بیلد کند.</i>"
        )
        bot.edit_message_text(success_text, chat_id=user_id, message_id=wait_msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ <b>خطا در ساخت پنل:</b>\n<code>{str(e)}</code>", chat_id=user_id, message_id=wait_msg.message_id)

@bot.message_handler(func=lambda msg: msg.text == "📋 پنل‌های من")
def my_panels(message):
    user_id = message.from_user.id
    panels = db.get_user_panels(user_id)

    if not panels:
        bot.send_message(user_id, "📭 شما هنوز هیچ پنلی نساخته‌اید.")
        return

    for p in panels:
        markup = types.InlineKeyboardMarkup()
        if p["domain"] and not p["domain"].startswith("در حال"):
            markup.add(types.InlineKeyboardButton("🌐 ورود به پنل", url=f"https://{p['domain']}"))
        markup.add(types.InlineKeyboardButton("🗑️ حذف پنل", callback_data=f"del_{p['id']}"))

        text = (
            f"📦 <b>پروژه:</b> <code>{p['project_name']}</code>\n"
            f"🌐 <b>دامنه:</b> <code>{p['domain']}</code>\n"
            f"📅 <b>تاریخ:</b> {p['created_at']}"
        )
        bot.send_message(user_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def handle_delete_panel(call):
    user_id = call.from_user.id
    panel_id = int(call.data.split("_")[1])
    panel = db.get_panel_by_id(panel_id)

    if not panel:
        bot.answer_callback_query(call.id, "پنل یافت نشد.")
        return

    user = db.get_user(user_id)
    if panel["user_id"] != user_id and not is_admin(user_id):
        bot.answer_callback_query(call.id, "دسترسی غیرمجاز!")
        return

    bot.answer_callback_query(call.id, "در حال حذف از Railway...")

    try:
        if user and user.get("railway_token"):
            railway_api.delete_project_api(user["railway_token"], panel["project_id"])
    except Exception as e:
        print(f"Delete API Error: {e}")

    db.delete_panel(panel_id)
    bot.edit_message_text("🗑️ این پنل با موفقیت حذف گردید.", chat_id=call.message.chat.id, message_id=call.message.message_id)

# ================= پنل ادمین =================

@bot.message_handler(func=lambda msg: msg.text == "👑 پنل مدیریت")
def admin_panel(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 آمار کلی", callback_data="admin_stats"),
        types.InlineKeyboardButton("🔄 تغییر ریپازیتوری", callback_data="admin_set_repo")
    )
    markup.add(
        types.InlineKeyboardButton("📋 همه پنل‌ها", callback_data="admin_all_panels"),
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")
    )

    current_repo = db.get_setting("default_repo", "hdzirxluci-hub/pablo-panel")
    bot.send_message(
        user_id,
        f"👑 <b>پنل مدیریت ربات</b>\n\n📌 <b>ریپازیتوری فعلی:</b>\n<code>{current_repo}</code>",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats_callback(call):
    if not is_admin(call.from_user.id):
        return
    users = db.get_all_users()
    panels = db.get_all_panels()
    active_tokens = sum(1 for u in users if u.get("railway_token"))

    text = (
        "📊 <b>آمار کل ربات:</b>\n\n"
        f"👥 کل کاربران: <b>{len(users)}</b>\n"
        f"🔑 کاربران با توکن فعال: <b>{active_tokens}</b>\n"
        f"🚀 کل پنل‌های ساخته‌شده: <b>{len(panels)}</b>"
    )
    bot.send_message(call.message.chat.id, text)

@bot.callback_query_handler(func=lambda call: call.data == "admin_set_repo")
def admin_set_repo_callback(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = "WAITING_FOR_NEW_REPO"
    bot.send_message(
        call.message.chat.id,
        "🔗 لطفاً لینک گیت‌هاب یا نام ریپازیتوری جدید را بفرستید:\n(مثال: <code>https://github.com/hdzirxluci-hub/pablo-panel</code>)"
    )

@bot.callback_query_handler(func=lambda call: call.data == "admin_all_panels")
def admin_all_panels_callback(call):
    if not is_admin(call.from_user.id):
        return
    panels = db.get_all_panels()
    if not panels:
        bot.send_message(call.message.chat.id, "هیچ پنلی در سیستم ثبت نشده است.")
        return

    for p in panels[:15]:  # نمایش ۱۵ پنل آخر
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🗑️ حذف اجباری", callback_data=f"del_{p['id']}"))
        text = (
            f"👤 <b>کاربر:</b> <code>{p['user_id']}</code>\n"
            f"📦 <b>پروژه:</b> <code>{p['project_name']}</code>\n"
            f"🌐 <b>دامنه:</b> <code>{p['domain']}</code>"
        )
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def admin_broadcast_callback(call):
    if not is_admin(call.from_user.id):
        return
    user_states[call.from_user.id] = "WAITING_FOR_BROADCAST"
    bot.send_message(call.message.chat.id, "📢 متن پیام همگانی را ارسال کنید:")

# ================= دریافت پیام‌های متنی و استیت‌ها =================

@bot.message_handler(func=lambda msg: True)
def handle_all_text(message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    # ثبت توکن
    if state == "WAITING_FOR_TOKEN":
        token = message.text.strip()
        try:
            wait_msg = bot.send_message(user_id, "🔍 در حال بررسی اعتبار توکن...")
            user_info = railway_api.check_token(token)
            db.set_user_token(user_id, token)
            user_states.pop(user_id, None)

            name = user_info.get("name") or user_info.get("email") or "کاربر Railway"
            bot.edit_message_text(
                f"✅ <b>توکن با موفقیت تأیید شد!</b>\n👤 حساب متصل: <b>{name}</b>\n\nحالا می‌توانید پنل بسازید.",
                chat_id=user_id,
                message_id=wait_msg.message_id
            )
        except Exception as e:
            bot.send_message(user_id, f"❌ <b>توکن نامعتبر است:</b>\n<code>{str(e)}</code>")

    # تغییر ریپازیتوری توسط ادمین
    elif state == "WAITING_FOR_NEW_REPO" and is_admin(user_id):
        new_repo = railway_api.clean_repo(message.text.strip())
        db.set_setting("default_repo", new_repo)
        user_states.pop(user_id, None)
        bot.send_message(user_id, f"✅ ریپازیتوری پیش‌فرض به <code>{new_repo}</code> تغییر یافت.")

    # ارسال پیام همگانی
    elif state == "WAITING_FOR_BROADCAST" and is_admin(user_id):
        user_states.pop(user_id, None)
        users = db.get_all_users()
        sent = 0
        for u in users:
            try:
                bot.send_message(u["user_id"], f"📢 <b>پیام مدیریت:</b>\n\n{message.text}")
                sent += 1
            except Exception:
                pass
        bot.send_message(user_id, f"✅ پیام به {sent} نفر ارسال شد.")

if __name__ == "__main__":
    print("🤖 Telegram Bot is running...")
    bot.infinity_polling(skip_pending=True)