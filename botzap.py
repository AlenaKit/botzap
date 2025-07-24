import logging
import datetime
import asyncio
import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ============== Налаштування =====================
API_TOKEN = "8194805573:AAEMzVKN3UW78NG723YKIuKdwn9M2rcUNOI"   # встав свій токен Telegram
SERVICE_ACCOUNT_FILE = "botzap-466905-c28e8b2e744c.json"  # назва твого JSON-файлу
GOOGLE_SHEET_ID = "602608749"                # ID твоєї Google таблиці
NOTIFY_USERS = [602608749, 5321616837]  # Telegram ID користувачів, яким надсилати повідомлення про новий запис

logging.basicConfig(level=logging.INFO)

# Авторизація Google Sheets
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
gc = gspread.authorize(credentials)
worksheet = gc.open_by_key(GOOGLE_SHEET_ID).sheet1

# Telegram bot
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# ===================== Клавіатури =====================

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Записати авто")],
        [KeyboardButton(text="📖 Переглянути записи")]
    ],
    resize_keyboard=True
)

services_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Комплекс", callback_data="service_Комплекс")],
        [InlineKeyboardButton(text="Полірування", callback_data="service_Полірування")],
        [InlineKeyboardButton(text="Хімчистка", callback_data="service_Хімчистка")],
        [InlineKeyboardButton(text="Поклейка плівки", callback_data="service_Поклейка плівки")],
        [InlineKeyboardButton(text="Інше", callback_data="service_Інше")]
    ]
)

def create_date_keyboard(prefix):
    today = datetime.date.today()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for i in range(7):
        day = today + datetime.timedelta(days=i)
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=day.strftime("%d.%m.%Y"), callback_data=f"{prefix}_{day}")
        ])
    return kb

def create_time_keyboard(prefix):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    start = datetime.time(8, 0)
    end = datetime.time(19, 30)
    t = datetime.datetime.combine(datetime.date.today(), start)
    end_dt = datetime.datetime.combine(datetime.date.today(), end)
    row = []
    while t <= end_dt:
        row.append(InlineKeyboardButton(text=t.strftime("%H:%M"), callback_data=f"{prefix}_{t.strftime('%H:%M')}"))
        if len(row) == 4:
            kb.inline_keyboard.append(row)
            row = []
        t += datetime.timedelta(minutes=15)
    if row:
        kb.inline_keyboard.append(row)
    return kb

# ===================== Обробники =====================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Вітаю! Оберіть дію:", reply_markup=main_kb)

# Змінні для тимчасових даних користувача
user_data = {}

@dp.message(lambda m: m.text == "📅 Записати авто")
async def start_booking(message: types.Message):
    await message.answer("Оберіть дату:", reply_markup=create_date_keyboard("bookingdate"))

@dp.callback_query(lambda c: c.data.startswith("bookingdate_"))
async def choose_booking_date(callback: types.CallbackQuery):
    date_str = callback.data.split("_", 1)[1]
    user_data[callback.from_user.id] = {"date": date_str}
    await callback.message.answer("Оберіть час:", reply_markup=create_time_keyboard("bookingtime"))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("bookingtime_"))
async def choose_booking_time(callback: types.CallbackQuery):
    time_str = callback.data.split("_", 1)[1]
    user_data[callback.from_user.id]["time"] = time_str
    await callback.message.answer("Введіть: Марка Модель Номер одним повідомленням")
    await callback.answer()

@dp.message(lambda m: m.from_user.id in user_data and "car" not in user_data[m.from_user.id])
async def get_car_info(message: types.Message):
    user_data[message.from_user.id]["car"] = message.text
    await message.answer("Оберіть послугу:", reply_markup=services_kb)

@dp.callback_query(lambda c: c.data.startswith("service_"))
async def choose_service(callback: types.CallbackQuery):
    service = callback.data.split("_", 1)[1]
    data = user_data.pop(callback.from_user.id)
    new_id = len(worksheet.get_all_values()) + 1
    worksheet.append_row([new_id, data["date"], data["time"], data["car"], service])

    # Повідомлення про новий запис
    for admin_id in NOTIFY_USERS:
        try:
            await bot.send_message(admin_id, 
                f"НОВИЙ ЗАПИС:\nДата: {data['date']}\nЧас: {data['time']}\nАвто: {data['car']}\nПослуга: {service}")
        except Exception as e:
            logging.warning(f"Не вдалося надіслати повідомлення {admin_id}: {e}")

    await callback.message.answer("Запис додано ✅", reply_markup=main_kb)
    await callback.answer()

@dp.message(lambda m: m.text == "📖 Переглянути записи")
async def view_records(message: types.Message):
    await message.answer("Оберіть дату:", reply_markup=create_date_keyboard("viewdate"))

@dp.callback_query(lambda c: c.data.startswith("viewdate_"))
async def view_records_date(callback: types.CallbackQuery):
    date_str = callback.data.split("_", 1)[1]
    records = worksheet.get_all_values()[1:]  # без заголовка
    filtered = [r for r in records if r[1] == date_str]
    if filtered:
        text = f"Записи на {date_str}:\n\n" + "\n".join(
            [f"{r[2]} | {r[3]} | {r[4]}" for r in filtered]
        )
    else:
        text = f"Записів на {date_str} немає."
    await callback.message.answer(text)
    await callback.answer()

# ===================== Запуск =====================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
