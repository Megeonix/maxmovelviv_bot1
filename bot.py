import logging
import os
import asyncio
import math
import signal
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from keep_alive import keep_alive
import requests

API_TOKEN = os.getenv("BOT_TOKEN")
ORS_API_KEY = os.getenv("ORS_API_KEY")
ADMIN_CHAT_IDS = [1364324881, 591264759]
LVIV_CENTER = (49.8419, 24.0315)
CITY_RADIUS_KM = 10

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=types.DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    TYPE = State()
    LOAD = State()
    DELIVER = State()
    HOURS = State()
    PHONE = State()
    CONFIRM = State()

user_data = {}
order_counter = 1

def get_distance_km(start, end):
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    body = {"coordinates": [[start[1], start[0]], [end[1], end[0]]]}
    try:
        r = requests.post(url, headers=headers, json=body)
        r.raise_for_status()
        dist = r.json()["features"][0]["properties"]["segments"][0]["distance"]
        return dist / 1000
    except Exception as e:
        print("Distance error:", e)
        return None

def haversine(coord1, coord2):
    R = 6371
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

@dp.message(commands=["start"])
async def start(message: types.Message, state: FSMContext):
    await state.set_state(Form.TYPE)
    kb = ReplyKeyboardBuilder()
    kb.add(KeyboardButton(text="По місту Львів"))
    kb.add(KeyboardButton(text="За межі міста"))
    await message.answer("🚚 <b>Максимум перевезень</b>\n\nОберіть тип перевезення:", reply_markup=kb.as_markup(resize_keyboard=True))

@dp.message(Form.TYPE)
async def select_type(message: types.Message, state: FSMContext):
    if message.text not in ["По місту Львів", "За межі міста"]:
        return await message.answer("Оберіть із клавіатури.")
    await state.update_data(type=message.text)
    await state.set_state(Form.LOAD)
    await message.answer("📍 Надішліть точку <b>завантаження</b>", reply_markup=types.ReplyKeyboardRemove())

@dp.message(Form.LOAD, content_types=["location"])
async def load_location(message: types.Message, state: FSMContext):
    await state.update_data(load=(message.location.latitude, message.location.longitude))
    await state.set_state(Form.DELIVER)
    await message.answer("📍 Надішліть точку <b>доставки</b>")

@dp.message(Form.DELIVER, content_types=["location"])
async def deliver_location(message: types.Message, state: FSMContext):
    data = await state.get_data()
    load = data["load"]
    deliver = (message.location.latitude, message.location.longitude)
    dist = get_distance_km(load, deliver)
    if dist is None:
        return await message.answer("❌ Не вдалося визначити відстань.")
    await state.update_data(deliver=deliver, distance=dist)
    if data["type"] == "По місту Львів":
        await state.set_state(Form.HOURS)
        return await message.answer(f"Відстань: {dist:.2f} км. Введіть кількість годин (мін. 2).")
    else:
        edge_dist = max(0, haversine(LVIV_CENTER, load) - CITY_RADIUS_KM)
        total_km = edge_dist + dist
        price = round((900 + total_km * 2 * 20) / 10) * 10
        await state.update_data(price=price)
        await state.set_state(Form.PHONE)
        kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[[KeyboardButton(text="📞 Поділитися номером", request_contact=True)]])
        await message.answer(f"Відстань: {dist:.2f} км. Орієнтовна вартість: {price} грн. Надішліть номер:", reply_markup=kb)

@dp.message(Form.HOURS)
async def process_hours(message: types.Message, state: FSMContext):
    try:
        hours = float(message.text.replace(",", "."))
    except:
        return await message.answer("Введіть число.")
    hours = max(2, hours)
    price = round((hours * 450) / 10) * 10
    await state.update_data(hours=hours, price=price)
    await state.set_state(Form.PHONE)
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[[KeyboardButton(text="📞 Поділитися номером", request_contact=True)]])
    await message.answer(f"Орієнтовна вартість: {price} грн. Надішліть номер:", reply_markup=kb)

@dp.message(Form.PHONE, content_types=["contact"])
async def contact_handler(message: types.Message, state: FSMContext):
    if message.contact.user_id != message.from_user.id:
        return await message.answer("Це не ваш номер.")
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(Form.CONFIRM)
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[[KeyboardButton(text="✅ Підтвердити заявку")]])
    await message.answer("✅ Підтвердити заявку?", reply_markup=kb)

@dp.message(Form.CONFIRM)
async def confirm(message: types.Message, state: FSMContext):
    if message.text != "✅ Підтвердити заявку":
        return
    global order_counter
    data = await state.get_data()
    order_id = f"#{datetime.now().strftime('%Y%m%d')}-{order_counter}"
    order_counter += 1
    text = (
        f"📦 <b>Нова заявка</b> {order_id}\n"
        f"Тип: {data['type']}\n"
        f"Звідки: <a href='https://maps.google.com/?q={data['load'][0]},{data['load'][1]}'>Google Maps</a>\n"
        f"Куди: <a href='https://maps.google.com/?q={data['deliver'][0]},{data['deliver'][1]}'>Google Maps</a>\n"
        f"Відстань: {data['distance']:.2f} км\n"
        f"Ціна: {data['price']} грн\n"
        f"Телефон: {data['phone']}\n"
        f"Час: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )
    for admin_id in ADMIN_CHAT_IDS:
        await bot.send_message(admin_id, text, disable_web_page_preview=True)
    await message.answer("✅ Дякуємо! Заявку надіслано.")
    await state.clear()

async def main():
    keep_alive()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())