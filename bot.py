import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import requests
from datetime import datetime
import math
from flask import Flask
from threading import Thread
import os

API_TOKEN = os.getenv("API_TOKEN")
ORS_API_KEY = os.getenv("ORS_API_KEY")
ADMIN_CHAT_IDS = [1364324881, 591264759]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

app = Flask('')

@app.route('/')
def home():
    return "Я живий!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

def main():
    keep_alive()
    executor.start_polling(dp, skip_updates=True)

if __name__ == '__main__':
    main()
