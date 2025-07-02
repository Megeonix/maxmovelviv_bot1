from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.types import Contact, Location
from aiogram.filters import Command
from services import process_distance, phone_keyboard, confirm_keyboard, get_order_text, user_data, FormState, ADMIN_CHAT_IDS
from datetime import datetime

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    user_data[message.from_user.id] = {"state": FormState.TYPE_SELECTION}
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[
        KeyboardButton(text="По місту Львів"), KeyboardButton(text="За межі міста")
    ]])
    text = (
    "🚚 <b>Максимум перевезень</b> — професійні вантажні перевезення у Львові та за його межами.\n\n"
    "Ми спеціалізуємось на квартирних, офісних та інших видах переїздів з вантажниками або без.\n\n"
    "<b>Оберіть тип перевезення:</b>"
)
    await message.answer(text, reply_markup=keyboard)

@router.message(F.text.in_(["По місту Львів", "За межі міста"]))
async def type_selected(message: Message):
    uid = message.from_user.id
    if user_data.get(uid, {}).get("state") != FormState.TYPE_SELECTION:
        return
    user_data[uid]["type"] = message.text
    user_data[uid]["state"] = FormState.LOAD_LOCATION
    await message.answer("📍 Надішліть точку <b>завантаження</b> (локація).", reply_markup=ReplyKeyboardRemove())

@router.message(F.location)
async def handle_location(message: Message):
    await process_distance(message)

@router.message(F.text.regexp(r'^\d+(\.\d+)?$'))
async def process_hours(message: Message):
    uid = message.from_user.id
    if user_data.get(uid, {}).get("state") != FormState.HOURS:
        return
    try:
        hours = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Введіть число.")
        return
    if hours < 2:
        hours = 2
    price = round(hours * 450 / 10) * 10
    user_data[uid]["hours"] = hours
    user_data[uid]["price"] = price
    user_data[uid]["state"] = FormState.PHONE
    await message.answer(f"Орієнтовна вартість: {price} грн. Введіть номер або натисніть кнопку нижче.", reply_markup=phone_keyboard())

@router.message(F.contact)
async def handle_contact(message: Message):
    uid = message.from_user.id
    if message.contact.user_id != uid:
        await message.answer("Це не ваш номер.")
        return
    user_data[uid]["phone"] = message.contact.phone_number
    user_data[uid]["state"] = FormState.CONFIRM
    await message.answer("✅ Підтвердити заявку?", reply_markup=confirm_keyboard())

@router.message(F.text == "✅ Підтвердити заявку")
async def handle_confirm(message: Message):
    uid = message.from_user.id
    if user_data.get(uid, {}).get("state") != FormState.CONFIRM:
        return
    order_text = get_order_text(uid, message.from_user)
    for admin in ADMIN_CHAT_IDS:
        await message.bot.send_message(admin, order_text)
    await message.answer("✅ Дякуємо! Заявку надіслано.")
    user_data.pop(uid, None)
