import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from flask import Flask
from threading import Thread
import requests
from datetime import datetime
import math

API_TOKEN = os.getenv("BOT_TOKEN")
ORS_API_KEY = os.getenv("ORS_API_KEY")
ADMIN_CHAT_IDS = [1364324881, 591264759]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=MemoryStorage())

app = Flask(__name__)
@app.route("/")
def home():
    return "Bot is running!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run_web)
    thread.start()

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
LVIV_CENTER = (49.8419, 24.0315)
CITY_RADIUS_KM = 10

def get_distance_km(start, end):
    url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    body = {"coordinates": [[start[1], start[0]], [end[1], end[0]]]}
    try:
        response = requests.post(url, json=body, headers=headers)
        response.raise_for_status()
        data = response.json()
        dist_m = data['features'][0]['properties']['segments'][0]['distance']
        return dist_m / 1000
    except Exception as e:
        print("Error getting distance:", e)
        return None

def haversine(coord1, coord2):
    R = 6371
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

@dp.message()
async def handle_message(message: types.Message):
    await message.answer("Бот працює!")

def start():
    import asyncio
    from aiogram import Router
    from aiogram.types import Message

    router = Router()
    dp.include_router(router)

    keep_alive()
    asyncio.run(dp.start_polling(bot))

if __name__ == "__main__":
    start()
