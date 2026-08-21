import os
import asyncio
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

# ===== ССЫЛКА НА РАБОЧИЙ СКРИПТ С САЙТА =====
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwyAmrGH6eB8itSXoFVDJvnaX9nPDwysQoTLuWP5VvshEYXMB1h0bYCkUKT4tBTrM9pNg/exec"

# Часовой пояс Екатеринбурга (UTC+5)
EKAT_TIMEZONE = timezone(timedelta(hours=5))

# ========== FSM (состояния) ==========
class OrderForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()

# ========== Бот ==========
storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# ========== Клавиатура ==========
main_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="📝 Оставить заявку")]
    ],
    resize_keyboard=True,
)

# ========== Обработчики ==========
@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "Здравствуйте! Я бот сервиса Borisov Store.\n"
        "Нажмите кнопку ниже, чтобы оставить заявку.",
        reply_markup=main_kb,
    )

@dp.message(Command("cancel"))
async def cancel_order(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активной заявки для отмены.")
        return
    await state.clear()
    await message.answer("Оформление заявки отменено.", reply_markup=main_kb)

# ===== НАЧАЛО ЗАЯВКИ =====
@dp.message(F.text == "📝 Оставить заявку")
async def start_order(message: types.Message, state: FSMContext):
    await state.set_state(OrderForm.waiting_for_name)
    await message.answer("Как вас зовут?")

# ===== ИМЯ =====
@dp.message(OrderForm.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.waiting_for_phone)
    await message.answer("Ваш номер телефона (в формате +7XXXXXXXXXX):")

# ===== ТЕЛЕФОН → ФИНАЛ =====
@dp.message(OrderForm.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not (phone.startswith("+") and phone[1:].isdigit() and len(phone) >= 12) and not (phone.isdigit() and len(phone) >= 11):
        await message.answer("Пожалуйста, введите корректный номер (11 цифр или +7XXXXXXXXXX).")
        return
    
    data = await state.get_data()
    name = data["name"]
    now_ekat = datetime.now(EKAT_TIMEZONE).strftime("%d.%m.%Y %H:%M")
    username = message.from_user.username or "без username"

    # ===== ОТПРАВКА ДАННЫХ В ТАБЛИЦУ (через data= для совместимости со скриптом сайта) =====
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "date": now_ekat,
                "name": name,
                "phone": phone,
                "nick": f"@{username}"
            }
            # Отправляем как form data (data=), а не json=
            async with session.post(GOOGLE_SCRIPT_URL, data=payload) as resp:
                response_text = await resp.text()
                print(f"Google Sheets ответил: {response_text}")
        except Exception as e:
            print(f"ОШИБКА записи в таблицу: {e}")

    await state.clear()
    await message.answer(
        "Спасибо! Сергей свяжется с вами в ближайшее время.",
        reply_markup=main_kb
    )

# ===== УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК =====
@dp.message()
async def any_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Здравствуйте! Я бот сервиса Borisov Store.\n"
            "Нажмите кнопку ниже, чтобы оставить заявку.",
            reply_markup=main_kb,
        )

# ========== HTTP-сервер для Render ==========
async def handle(request):
    return web.Response(text="Bot is running")

async def health(request):
    return web.Response(text="OK")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    app.router.add_get("/health", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"HTTP server started on port {PORT}")

async def delete_webhook():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook") as resp:
            result = await resp.json()
            print(f"Webhook deleted: {result}")

async def main():
    await delete_webhook()
    await run_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
