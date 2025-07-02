from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
import requests
import math

ADMIN_CHAT_IDS = [1364324881, 591264759]
ORS_API_KEY = "5b3ce3597851110001cf6248aa59ec61e83c41059f923ebaff9a9868"
LVIV_CENTER = (49.8419, 24.0315)
CITY_RADIUS_KM = 10

class FormState:
    START = 0
    TYPE_SELECTION = 1
    LOAD_LOCATION = 2
    DELIVERY_LOCATION = 3
    HOURS = 4
    PHONE = 5
    CONFIRM = 6

user_data = {}
order_counter = 1

def get_distance_km(start, end):
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    body = {"coordinates": [[start[1], start[0]], [end[1], end[0]]]}
    try:
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
        dist = response.json()["features"][0]["properties"]["segments"][0]["distance"]
        return dist / 1000
    except:
        return None

def haversine(coord1, coord2):
    R = 6371
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def phone_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[[
        KeyboardButton(text="📞 Поділитися номером", request_contact=True)
    ]])

def confirm_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[[
        KeyboardButton(text="✅ Підтвердити заявку")
    ]])

async def process_distance(message: Message):
    uid = message.from_user.id
    state = user_data.get(uid, {}).get("state")
    loc = (message.location.latitude, message.location.longitude)
    if state == FormState.LOAD_LOCATION:
        user_data[uid]["load_location"] = loc
        user_data[uid]["state"] = FormState.DELIVERY_LOCATION
        await message.answer("📍 Надішліть точку доставки.")
    elif state == FormState.DELIVERY_LOCATION:
        user_data[uid]["delivery_location"] = loc
        load = user_data[uid]["load_location"]
        delivery = user_data[uid]["delivery_location"]
        dist = get_distance_km(load, delivery)
        if dist is None:
            await message.answer("Не вдалося визначити відстань.")
            return
        user_data[uid]["distance_km"] = dist
        if user_data[uid]["type"] == "По місту Львів":
            user_data[uid]["state"] = FormState.HOURS
            await message.answer(f"Відстань: {dist:.2f} км. Введіть кількість годин (мін. 2).")
        else:
            dist_from_edge = max(0, haversine(LVIV_CENTER, load) - CITY_RADIUS_KM)
            total_km = dist + dist_from_edge
            price = 900 + total_km * 2 * 20
            user_data[uid]["price"] = round(price / 10) * 10
            user_data[uid]["state"] = FormState.PHONE
            await message.answer(f"Вартість: {user_data[uid]['price']} грн. Введіть номер або натисніть кнопку нижче.", reply_markup=phone_keyboard())

def get_order_text(uid, user):
    global order_counter
    data = user_data[uid]
    order_id = f"#{datetime.now().strftime('%Y%m%d')}-{order_counter}"
    order_counter += 1
    return (
        f"📦 <b>Нова заявка</b> {order_id}\n"
        f"Тип: {data.get('type')}\n"
        f"Звідки: https://maps.google.com/?q={data['load_location'][0]},{data['load_location'][1]}\n"
        f"Куди: https://maps.google.com/?q={data['delivery_location'][0]},{data['delivery_location'][1]}\n"
        f"Відстань: {data.get('distance_km', 0):.2f} км\n"
        f"Ціна: {data.get('price')} грн\n"
        f"Телефон: {data.get('phone')}\n"
        f"Користувач: @{user.username or user.full_name}\n"
        f"Час: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
    )