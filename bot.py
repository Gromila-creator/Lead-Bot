import os
import asyncio
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime, timezone, timedelta  # <-- добавлено
from dotenv import load_dotenv

# Google Sheets временно отключён
# import gspread
# from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

# ===== ТВОЙ TELEGRAM ID =====
ADMIN_CHAT_ID = 990317436

# Часовой пояс Екатеринбурга (UTC+5)
EKAT_TIMEZONE = timezone(timedelta(hours=5))

# ========== FSM ==========
class OrderForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_question = State()

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
        "Здравствуйте! Я бот для сбора заявок.\n"
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

@dp.message(F.text == "📝 Оставить заявку")
async def start_order(message: types.Message, state: FSMContext):
    await state.set_state(OrderForm.waiting_for_name)
    await message.answer("Как вас зовут?")

@dp.message(OrderForm.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.waiting_for_phone)
    await message.answer("Ваш номер телефона (в формате +7XXXXXXXXXX):")

@dp.message(OrderForm.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not (phone.startswith("+") and phone[1:].isdigit() and len(phone) >= 12) and not (phone.isdigit() and len(phone) >= 11):
        await message.answer("Пожалуйста, введите корректный номер (11 цифр или +7XXXXXXXXXX).")
        return
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.waiting_for_question)
    await message.answer("Что вас интересует? (кратко опишите вопрос)")

@dp.message(OrderForm.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    phone = data["phone"]
    question = message.text
    # Время по Екатеринбургу (UTC+5)
    now_ekat = datetime.now(EKAT_TIMEZONE).strftime("%d.%m.%Y %H:%M")
    username = message.from_user.username or "без username"

    # ===== ОТПРАВКА УВЕДОМЛЕНИЯ АДМИНУ =====
    try:
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"🆕 <b>Новая заявка!</b>\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Вопрос: {question}\n"
            f"Дата: {now_ekat} (Екатеринбург)\n"
            f"Ник: @{username}",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление админу: {e}")

    # ===== ЗАПИСЬ В ТАБЛИЦУ (ПОКА ОТКЛЮЧЕНА) =====
    # try:
    #     sheet = gspread_client.open_by_key(SHEET_ID).sheet1
    #     await asyncio.to_thread(sheet.append_row, [now_ekat, name, phone, question, username])
    # except Exception as e:
    #     print(f"Ошибка записи в таблицу: {e}")

    await state.clear()
    await message.answer(
        "Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.",
        reply_markup=main_kb
    )

# ===== УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК =====
@dp.message()
async def any_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Здравствуйте! Я бот для сбора заявок.\n"
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
    app.router.add_get("/health", health)   # для проверки работоспособности
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
