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

# ===== ССЫЛКА НА ВАШ GOOGLE APPS SCRIPT =====
GOOGLE_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxXndEAQ7z8ZM9-AfHziDiHrtbfVMansIXGT0n02HNoNWZo4wIJF8fd7yPil3Oczisj8w/exec"

# ===== ТВОЙ TELEGRAM ID =====
ADMIN_CHAT_ID = 990317436

# Часовой пояс Екатеринбурга (UTC+5)
EKAT_TIMEZONE = timezone(timedelta(hours=5))

# ========== FSM (состояния) ==========
class OrderForm(StatesGroup):
    waiting_for_confirmation = State()  # новое состояние для ожидания "да"
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
        "Здравствуйте! Я бот сервиса Borisov Store. Мы создаем сайты.\n"
        "Нажмите кнопку ниже, чтобы увидеть наши услуги и цены.",
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

# ===== НАЧАЛО ЗАЯВКИ: показываем прайс и просим подтверждение =====
@dp.message(F.text == "📝 Оставить заявку")
async def start_order(message: types.Message, state: FSMContext):
    # Полный прайс с чёткими цифрами (без "от")
    price_text = (
        "📋 <b>Наши услуги и цены</b>\n\n"
        "🔹 <b>Лендинг</b> — 8 000 ₽\n"
        "🔹 <b>Информационный сайт</b> — 12 000 ₽\n"
        "🔹 <b>Сайт-визитка</b> — 16 000 ₽\n"
        "🔹 <b>Портфолио</b> — 20 000 ₽\n"
        "🔹 <b>Интернет-магазин</b> — 24 000 ₽\n"
        "🔹 <b>Универсальный сайт</b> — 40 000 ₽\n\n"
        "➕ <b>Дополнительные услуги:</b>\n"
        "• Бесплатно установим: favicon, логотипы, контакты, ссылки на оплату\n"
        "• Форма обратной связи (Formspree) — 1 600 ₽\n"
        "• Карта проезда — 1 600 ₽\n"
        "• Всплывающий виджет для звонка — 2 400 ₽\n"
        "• Блок «Отзывы» — 2 400 ₽\n"
        "• Страница «Договор оферты» — 2 400 ₽\n"
        "• Страница «Политика конфиденциальности» — 2 400 ₽\n"        
        "• Добавление 6 товаров (для интернет-магазина) — 2 400 ₽\n"
        "• Установка Яндекс-Метрики — 2 400 ₽\n"
        "• Еще 2 товара (для лендинга) — 4 000 ₽\n"
        "• Автоматическая оплата (ЮKassa) — 4 000 ₽\n"
        "• Интеграция с календарём — 4 000 ₽\n"
        "• Приём заказов в Google Таблицу — 4 000 ₽\n\n"
        "Теперь, когда вы знаете цены, напишите <b>«да»</b>, и мы продолжим оформление заявки."
    )
    await message.answer(price_text, parse_mode="HTML")
    await state.set_state(OrderForm.waiting_for_confirmation)

# ===== ОЖИДАНИЕ ПОДТВЕРЖДЕНИЯ («да») =====
@dp.message(OrderForm.waiting_for_confirmation)
async def confirm_order(message: types.Message, state: FSMContext):
    if message.text.lower() == "да":
        # Переходим к сбору имени
        await state.set_state(OrderForm.waiting_for_name)
        await message.answer("Как вас зовут?")
    else:
        await message.answer(
            "Пожалуйста, напишите <b>«да»</b>, чтобы продолжить оформление заявки, "
            "или отправьте /cancel, чтобы отменить.",
            parse_mode="HTML"
        )

# ===== ИМЯ =====
@dp.message(OrderForm.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.waiting_for_phone)
    await message.answer("Ваш номер телефона (в формате +7XXXXXXXXXX):")

# ===== ТЕЛЕФОН =====
@dp.message(OrderForm.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip()
    if not (phone.startswith("+") and phone[1:].isdigit() and len(phone) >= 12) and not (phone.isdigit() and len(phone) >= 11):
        await message.answer("Пожалуйста, введите корректный номер (11 цифр или +7XXXXXXXXXX).")
        return
    await state.update_data(phone=phone)
    await state.set_state(OrderForm.waiting_for_question)
    await message.answer("Что вас интересует? (выберите нужные услуги)")

# ===== ВОПРОС → ФИНАЛ =====
@dp.message(OrderForm.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    phone = data["phone"]
    question = message.text
    now_ekat = datetime.now(EKAT_TIMEZONE).strftime("%d.%m.%Y %H:%M")
    username = message.from_user.username or "без username"

    # ===== ОТПРАВКА УВЕДОМЛЕНИЯ АДМИНУ =====
    try:
        await bot.send_message(
            ADMIN_CHAT_ID,
            f"🆕 <b>Новая заявка!</b>\n"
            f"Имя: {name}\n"
            f"Телефон: {phone}\n"
            f"Заказ: {question}\n"
            f"Дата: {now_ekat}\n"
            f"Ник: @{username}",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось отправить уведомление админу: {e}")

    # ===== ЗАПИСЬ В ТАБЛИЦУ (Google Apps Script) =====
    async with aiohttp.ClientSession() as session:
        try:
            payload = {
                "date": now_ekat,
                "name": name,
                "phone": phone,
                "nick": f"@{username}",
                "question": question
            }
            async with session.post(GOOGLE_SCRIPT_URL, json=payload) as resp:
                response_text = await resp.text()
                print(f"Google Sheets ответил: {response_text}")
        except Exception as e:
            print(f"ОШИБКА записи в таблицу: {e}")

    await state.clear()
    await message.answer(
        "Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.",
        reply_markup=main_kb
    )

# ===== УНИВЕРСАЛЬНЫЙ ОБРАБОТЧИК ДЛЯ ЛЮБЫХ СООБЩЕНИЙ (вне заявки) =====
@dp.message()
async def any_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "Здравствуйте! Я бот сервиса Borisov Store. Мы создаем сайты.\n"
            "Нажмите кнопку ниже, чтобы увидеть наши услуги и цены.",
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
