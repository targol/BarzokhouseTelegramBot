# -*- coding: utf-8 -*-
"""
ربات رزرو اقامتگاه بومگردی «خانه برزک»
----------------------------------------
اجرا:
    python bot.py

قبل از اجرا حتما فایل config.py رو با اطلاعات واقعی خودت پر کن.
"""

import logging
import os

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# وضعیت‌های مکالمه‌ی رزرو
# ---------------------------------------------------------------------------
ASK_NAME, ASK_PHONE, ASK_CHECKIN, ASK_NIGHTS, ASK_GUESTS = range(5)


def to_english_digits(text: str) -> str:
    """تبدیل ارقام فارسی/عربی به انگلیسی، برای اعتبارسنجی راحت‌تر عدد."""
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    translation = {}
    for i, ch in enumerate(persian_digits):
        translation[ch] = str(i)
    for i, ch in enumerate(arabic_digits):
        translation[ch] = str(i)
    return "".join(translation.get(ch, ch) for ch in text)

# ---------------------------------------------------------------------------
# کیبوردهای کمکی
# ---------------------------------------------------------------------------
def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🛏 اتاق‌ها", callback_data="menu_rooms")],
        [InlineKeyboardButton("🍽 منوی غذا", callback_data="menu_food")],
        [InlineKeyboardButton("📜 قوانین و اطلاعات اقامت", callback_data="menu_rules")],
        [InlineKeyboardButton("📍 آدرس", callback_data="menu_address")],
        [InlineKeyboardButton("📞 تماس با ما", callback_data="menu_contact")],
        [InlineKeyboardButton("🌐 شبکه‌های اجتماعی", callback_data="menu_social")],
        [InlineKeyboardButton("⭐ ثبت نظر درباره اقامت شما", callback_data="menu_review")],
    ]
    return InlineKeyboardMarkup(buttons)


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ بازگشت به منو", callback_data="back_main")]]
    )


def rooms_list_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    for key, room in config.ROOMS.items():
        buttons.append(
            [InlineKeyboardButton(room["title"], callback_data=f"room_{key}")]
        )
    buttons.append([InlineKeyboardButton("⬅️ بازگشت به منو", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def room_detail_keyboard(room_key: str) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("✅ درخواست رزرو", callback_data=f"book_{room_key}")],
        [InlineKeyboardButton("⬅️ بازگشت به لیست اتاق‌ها", callback_data="menu_rooms")],
    ]
    return InlineKeyboardMarkup(buttons)


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📱 ارسال شماره تماس من", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ---------------------------------------------------------------------------
# دستور /start
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        config.WELCOME_MESSAGE, reply_markup=main_menu_keyboard()
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "درخواست رزرو لغو شد. هر وقت خواستی می‌تونی دوباره از /start شروع کنی.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# مدیریت دکمه‌های منوی اصلی (غیر از رزرو)
# ---------------------------------------------------------------------------
async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_main":
        await query.edit_message_text(
            config.WELCOME_MESSAGE, reply_markup=main_menu_keyboard()
        )
        return

    if data == "menu_address":
        await query.edit_message_text(
            config.ADDRESS_TEXT, reply_markup=back_to_main_keyboard()
        )
        await context.bot.send_location(
            chat_id=query.message.chat_id,
            latitude=config.LOCATION_LATITUDE,
            longitude=config.LOCATION_LONGITUDE,
        )
        return

    if data == "menu_contact":
        await query.edit_message_text(
            config.CONTACT_TEXT, reply_markup=back_to_main_keyboard()
        )
        return

    if data == "menu_social":
        await query.edit_message_text(
            config.SOCIAL_TEXT, reply_markup=back_to_main_keyboard()
        )
        return

    if data == "menu_food":
        await query.edit_message_text(
            config.FOOD_MENU_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_to_main_keyboard(),
        )
        return

    if data == "menu_rules":
        # این بخش چند پیام جداگانه می‌فرسته (متن + متن + عکس)، پس پیام قبلی رو حذف می‌کنیم
        try:
            await query.message.delete()
        except Exception:
            pass

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=config.HOUSE_RULES_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=config.WEATHER_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

        green_photo_path = config.GREEN_TRIP_PHOTO
        if green_photo_path and os.path.exists(green_photo_path):
            with open(green_photo_path, "rb") as photo_file:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=photo_file,
                    caption=config.GREEN_TRIP_TEXT,
                    parse_mode="HTML",
                    reply_markup=back_to_main_keyboard(),
                )
        else:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=config.GREEN_TRIP_TEXT,
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_markup=back_to_main_keyboard(),
            )
        return

    if data == "menu_review":
        await query.edit_message_text(
            config.REVIEW_TEXT,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=back_to_main_keyboard(),
        )
        return

    if data == "menu_rooms":
        await query.edit_message_text(
            "🛏 لیست اتاق‌های اقامتگاه:\nیکی از اتاق‌ها رو برای دیدن جزئیات انتخاب کن 👇",
            reply_markup=rooms_list_keyboard(),
        )
        return

    if data.startswith("room_"):
        room_key = data.replace("room_", "")
        room = config.ROOMS.get(room_key)
        if not room:
            await query.edit_message_text("متاسفانه این اتاق پیدا نشد.")
            return

        caption = f"🛏 {room['title']}\n\n{room['description']}\n\n💰 {room['price']}"
        photo_path = room.get("photo")

        # پیام قبلی (لیست اتاق‌ها) رو حذف می‌کنیم و عکس اتاق رو با کپشن می‌فرستیم
        try:
            await query.message.delete()
        except Exception:
            pass

        if photo_path and os.path.exists(photo_path):
            with open(photo_path, "rb") as photo_file:
                await context.bot.send_photo(
                    chat_id=query.message.chat_id,
                    photo=photo_file,
                    caption=caption,
                    reply_markup=room_detail_keyboard(room_key),
                )
        else:
            # اگر عکس پیدا نشد فقط متن ارسال میشه
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=caption,
                reply_markup=room_detail_keyboard(room_key),
            )
        return


# ---------------------------------------------------------------------------
# مکالمه‌ی رزرو
# ---------------------------------------------------------------------------
async def book_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    room_key = query.data.replace("book_", "")
    room = config.ROOMS.get(room_key)

    if not room:
        await query.message.reply_text("متاسفانه این اتاق پیدا نشد.")
        return ConversationHandler.END

    context.user_data["booking_room_key"] = room_key
    context.user_data["booking_room_title"] = room["title"]
    context.user_data["booking_room_price"] = room["price"]

    await query.message.reply_text(
        f"برای رزرو «{room['title']}» ({room['price']}) ابتدا لطفاً نام و نام خانوادگی خودتون رو وارد کنید:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def book_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text.strip()
    if len(name) < 3:
        await update.message.reply_text("لطفاً یک نام معتبر وارد کنید:")
        return ASK_NAME

    context.user_data["booking_name"] = name
    await update.message.reply_text(
        "سپاس! حالا لطفاً شماره تماس خودتون رو وارد کنید یا با دکمه زیر ارسال کنید:",
        reply_markup=phone_request_keyboard(),
    )
    return ASK_PHONE


async def book_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.contact:
        phone = update.message.contact.phone_number
    else:
        phone = update.message.text.strip()

    if len(phone) < 10:
        await update.message.reply_text("لطفاً یک شماره تماس معتبر وارد کنید:")
        return ASK_PHONE

    context.user_data["booking_phone"] = phone
    await update.message.reply_text(
        "ممنون! حالا لطفاً تاریخ ورود خودتون رو وارد کنید (مثلاً ۱۴۰۳/۰۵/۱۰):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_CHECKIN


async def book_get_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    checkin_date = update.message.text.strip()
    if len(checkin_date) < 4:
        await update.message.reply_text("لطفاً یک تاریخ معتبر وارد کنید (مثلاً ۱۴۰۳/۰۵/۱۰):")
        return ASK_CHECKIN

    context.user_data["booking_checkin"] = checkin_date
    await update.message.reply_text("تعداد شب‌های اقامت رو وارد کنید (مثلاً 2):")
    return ASK_NIGHTS


async def book_get_nights(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    nights_raw = to_english_digits(update.message.text.strip())
    if not nights_raw.isdigit() or int(nights_raw) < 1:
        await update.message.reply_text("لطفاً تعداد شب رو به‌صورت عدد وارد کنید (مثلاً 2):")
        return ASK_NIGHTS

    context.user_data["booking_nights"] = nights_raw
    await update.message.reply_text("تعداد نفرات رو وارد کنید (مثلاً 2):")
    return ASK_GUESTS


async def book_get_guests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    guests_raw = to_english_digits(update.message.text.strip())
    if not guests_raw.isdigit() or int(guests_raw) < 1:
        await update.message.reply_text("لطفاً تعداد نفرات رو به‌صورت عدد وارد کنید (مثلاً 2):")
        return ASK_GUESTS

    context.user_data["booking_guests"] = guests_raw
    await finalize_booking(update, context)
    return ConversationHandler.END


async def finalize_booking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    room_title = context.user_data.get("booking_room_title")
    room_price = context.user_data.get("booking_room_price")
    name = context.user_data.get("booking_name")
    phone = context.user_data.get("booking_phone")
    checkin = context.user_data.get("booking_checkin")
    nights = context.user_data.get("booking_nights")
    guests = context.user_data.get("booking_guests")

    # پیام برای مدیر اقامتگاه
    admin_text = (
        "🔔 درخواست رزرو جدید\n\n"
        f"🛏 اتاق: {room_title}\n"
        f"💰 قیمت: {room_price}\n"
        f"👤 نام: {name}\n"
        f"📞 شماره تماس: {phone}\n"
        f"📅 تاریخ ورود: {checkin}\n"
        f"🌙 تعداد شب: {nights}\n"
        f"👥 تعداد نفرات: {guests}\n"
        f"🆔 آیدی تلگرام: @{user.username if user.username else 'ندارد'}"
    )

    try:
        await context.bot.send_message(
            chat_id=config.ADMIN_CHAT_ID, text=admin_text, parse_mode="HTML"
        )
    except Exception as exc:
        logger.error("ارسال پیام به مدیر با خطا مواجه شد: %s", exc)

    await update.message.reply_text(
        "✅ درخواست رزرو شما با موفقیت ثبت و برای مدیریت اقامتگاه ارسال شد.\n"
        "به‌زودی برای هماهنگی نهایی با شما تماس گرفته می‌شود.\n\n"
        "برای بازگشت به منوی اصلی /start رو بزنید.",
        reply_markup=ReplyKeyboardRemove(),
    )
    context.user_data.clear()


# ---------------------------------------------------------------------------
# راه‌اندازی ربات
# ---------------------------------------------------------------------------
def main() -> None:
    token = os.environ.get("BOT_TOKEN", config.BOT_TOKEN)
    if token == "PUT_YOUR_BOT_TOKEN_HERE":
        raise SystemExit(
            "لطفاً ابتدا توکن ربات رو وارد کنید (در config.py یا متغیر محیطی BOT_TOKEN)."
        )

    application = Application.builder().token(token).build()

    booking_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(book_start, pattern=r"^book_")],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_get_name)],
            ASK_PHONE: [
                MessageHandler(
                    (filters.TEXT & ~filters.COMMAND) | filters.CONTACT, book_get_phone
                )
            ],
            ASK_CHECKIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_get_checkin)],
            ASK_NIGHTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_get_nights)],
            ASK_GUESTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_get_guests)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(booking_conv)
    application.add_handler(CallbackQueryHandler(menu_router))

    # اگر متغیر محیطی WEBHOOK_URL تنظیم شده باشه (مثلا موقع دیپلوی روی Render)
    # ربات با webhook اجرا میشه، در غیر این صورت با polling (مناسب اجرای لوکال روی سیستم خودت)
    webhook_url = os.environ.get("WEBHOOK_URL") or os.environ.get("RENDER_EXTERNAL_URL")
    if webhook_url:
        port = int(os.environ.get("PORT", "10000"))
        url_path = token  # مسیر مخفی وبهوک؛ حدس زدنش سخته چون خود توکنه
        logger.info("ربات در حالت webhook روی پورت %s اجرا میشه...", port)
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=url_path,
            webhook_url=f"{webhook_url.rstrip('/')}/{url_path}",
        )
    else:
        logger.info("ربات در حالت polling (اجرای لوکال) در حال اجراست...")
        application.run_polling()


if __name__ == "__main__":
    main()
