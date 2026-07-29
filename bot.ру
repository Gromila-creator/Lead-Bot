import os
import asyncio
import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from openai import AsyncOpenAI
from datetime import datetime
from dotenv import load_dotenv

# ========== ВРЕМЕННО ОТКЛЮЧАЕМ GOOGLE SHEETS ==========
# import gspread
# from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
SITE_URL = "https://borisov.store"
PORT = int(os.getenv("PORT", 10000))

# Эти переменные пока захардкожены, но вы потом можете вынести их в окружение
SHEET_ID = "ТВОЙ_SHEET_ID"          # пока не используется
ADMIN_CHAT_ID = 123456789           # пока не используется

# ========== Google Sheets авторизация (временно отключена) ==========
# scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
# gspread_client = gspread.authorize(creds)

# ========== БАЗА ЗНАНИЙ (без изменений) ==========
KNOWLEDGE = """
Ты — официальный представитель и консультант сервиса borisov.store.
Твоя задача — помогать клиентам, используя только информацию ниже. Запрещено вставлять прямые ссылки в текст ответа. Используй кнопку «Перейти на сайт».

О СЕРВИСЕ:
borisov.store — сервис по созданию сайтов на бесплатном хостинге GitHub Pages.
Исполнитель: Борисов Сергей, самозанятый.
Мы создаем качественные и функциональные сайты. Чтобы попасть на наш сайт нажмите кнопку «Перейти на сайт» под этим сообщением.

НАШИ ТЕХНОЛОГИИ:
Ваш сайт будет построен на трёх надёжных технологиях:

**HTML5** – «скелет» сайта:
• Семантическая вёрстка для лучшего понимания поисковиками
• Адаптивность: корректное отображение на любых устройствах
• Современные формы: удобный ввод данных
• Отложенная загрузка: высокая скорость работы
• Кроссбраузерность: Chrome, Firefox, Safari, Edge, Яндекс.Браузер
• Чистый код без устаревших тегов

**CSS3** – «одежда» сайта:
• Современный дизайн: тени, градиенты, плавные переходы
• Адаптивная вёрстка под все экраны
• Красивая типографика: шрифты, отступы, читаемость
• Анимация кнопок и элементов без замедления
• Flexbox и Grid для идеального позиционирования
• Лёгкость: стили вместо тяжёлых картинок

**JavaScript** – «поведение» сайта:
• Интерактивность: кнопки, меню, формы реагируют на действия
• Плавная прокрутка и модальные окна
• Проверка форм при вводе (email, телефон)
• Динамический контент без перезагрузки страницы
• Повышение конверсии: анимация важных элементов

**Мини-CRM на Google Таблицах**:
• Все заявки автоматически попадают в Google Таблицу и дублируются вам на почту

**Приём платежей через ЮKassa**:
• Автоматическая, безопасная и надёжная оплата для ваших клиентов
• Поддержка банковских карт, электронных кошельков и СБП

ПОРЯДОК РАБОТЫ И ОПЛАТА:
- Клиент выбирает тариф или согласовывает индивидуальный заказ.
- Желательно обсудить техническое задание (ТЗ) перед выполнением работ.
- Для начала работы нужны: материалы, ТЗ, доступ к GitHub (email и пароль).
- Оплата: предоплата 50% в начале работы, вторые 50% после приёмки.
- Срок разработки: до 3 рабочих дней (в сложных случаях до 7). Подробнее — в пункте 3.7 оферты.
- Бесплатный хостинг: GitHub Pages.
- Гарантийная поддержка: 30 дней.
- Доработки после гарантии: от 2000 руб.
- Условия сдачи и приемки сайта прописаны в оферте в п. 5.3.
- Домен оплачивается клиентом отдельно.

ПРЕИМУЩЕСТВА:
Подробно о преимуществах можно узнать, нажав кнопку «Перейти на сайт» — вы попадёте в раздел «Почему выбирают нас».

НАВИГАЦИЯ:
Если клиент спрашивает о чём-то, чего нет в базе, предложи нажать «Перейти на сайт» для перехода в нужный раздел.
"""

BUTTON_LINKS = {
    "🛠 Наши услуги": "https://borisov.store/#services",
    "🚚 Сроки и доставка": "https://borisov.store/offer/",
    "💳 Оплата": "https://borisov.store/#pricing",
    "↩️ Гарантии": "https://borisov.store/offer/",
    "📞 Контакты": "https://borisov.store/#contacts",
    "🛡 Проверка самозанятого": "https://npd.nalog.ru/check-status/",
    "⚙️ Технологии": SITE_URL,
    "⚡ Преимущества": "https://borisov.store/#advantages",
}

OFFER_KEYWORDS = ["тз", "задание", "оферт", "договор", "ознакомиться"]

def is_offer_request(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in OFFER_KEYWORDS)

SELFEMPLOYED_KEYWORDS = ["самозанят", "проверк", "статус", "налог", "инн"]

def is_selfemployed_request(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SELFEMPLOYED_KEYWORDS)

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_KEY,
)

class OrderForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_question = State()

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)
menu_shown = set()

main_kb = types.ReplyKeyboardMarkup(
    keyboard=[
        [types.KeyboardButton(text="🛠 Наши услуги"), types.KeyboardButton(text="🚚 Сроки и доставка")],
        [types.KeyboardButton(text="💳 Оплата"), types.KeyboardButton(text="↩️ Гарантии")],
        [types.KeyboardButton(text="📞 Контакты"), types.KeyboardButton(text="🛡 Проверка самозанятого")],
        [types.KeyboardButton(text="⚙️ Технологии"), types.KeyboardButton(text="⚡ Преимущества")],
        [types.KeyboardButton(text="📝 Оставить заявку")],
    ],
    resize_keyboard=True,
)

@dp.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    menu_shown.add(user_id)
    await message.answer(
        "Здравствуйте! Я виртуальный консультант сервиса borisov.store.\n"
        "Я расскажу об услугах, сроках, оплате и гарантиях.\n"
        "Задайте вопрос или воспользуйтесь кнопками ниже.",
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
    await message.answer("Давайте оформим заявку.\n\nКак вас зовут?")

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
    await message.answer("Что вас интересует? (кратко опишите вопрос или выберите из меню)")

@dp.message(OrderForm.waiting_for_question)
async def process_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    phone = data["phone"]
    question = message.text
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    user = message.from_user.username or "без username"

    # ========== ВРЕМЕННО ОТКЛЮЧАЕМ ЗАПИСЬ В ТАБЛИЦУ ==========
    # try:
    #     sheet = gspread_client.open_by_key(SHEET_ID).sheet1
    #     await asyncio.to_thread(sheet.append_row, [now, name, phone, question, user])
    # except Exception as e:
    #     print(f"Ошибка записи в таблицу: {e}")
    #     await message.answer("Извините, произошла ошибка при сохранении заявки. Пожалуйста, попробуйте позже.")
    #     await state.clear()
    #     return

    # ПОКА ПРОСТО ВЫВОДИМ В КОНСОЛЬ (ЗАЯВКА ПРИНЯТА, НО НЕ СОХРАНЯЕТСЯ)
    print(f"НОВАЯ ЗАЯВКА: {name}, {phone}, {question}, {now}, @{user}")

    # Уведомление админу (пока тоже отключим, чтобы не падало из-за ADMIN_CHAT_ID)
    # try:
    #     await bot.send_message(
    #         ADMIN_CHAT_ID,
    #         f"🆕 <b>Новая заявка!</b>\n"
    #         f"Имя: {name}\n"
    #         f"Телефон: {phone}\n"
    #         f"Вопрос: {question}\n"
    #         f"Дата: {now}\n"
    #         f"От: @{user}",
    #         parse_mode="HTML"
    #     )
    # except Exception as e:
    #     print(f"Не удалось отправить уведомление админу: {e}")

    await state.clear()
    await message.answer(
        "Спасибо! Ваша заявка принята. Мы свяжемся с вами в ближайшее время.",
        reply_markup=main_kb
    )

@dp.message()
async def handle_question(message: types.Message):
    user_text = message.text
    user_id = message.from_user.id
    await bot.send_chat_action(message.chat.id, "typing")

    if user_text == "⚙️ Технологии":
        answer = (
            "🛠 <b>Наши технологии</b>\n\n"
            "🔹 <b>HTML5</b> — структура и разметка. Семантическая вёрстка, адаптивность, корректное отображение в любых браузерах.\n\n"
            "🔹 <b>CSS3</b> — дизайн и стили. Современный внешний вид, анимации, идеальная раскладка на всех устройствах.\n\n"
            "🔹 <b>JavaScript</b> — интерактивность и поведение. Умные формы, плавные переходы, динамический контент без перезагрузки.\n\n"
            "📊 <b>Мини-CRM на Google Таблицах</b> — все заявки попадают в таблицу и дублируются вам на почту. Без лимитов.\n\n"
            "💳 <b>Приём платежей через ЮKassa</b> — автоматическая, безопасная и надёжная оплата через СБП и карты."
        )
        inline_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="Перейти на сайт", url=SITE_URL)]]
        )
        await message.answer(answer, reply_markup=inline_kb, parse_mode="HTML")
        return

    if user_text == "↩️ Гарантии":
        answer = (
            "На сервисе borisov.store мы предоставляем гарантийную поддержку в течение 30 дней после завершения разработки.\n\n"            
            "Для получения более подробной информации, пожалуйста, нажмите кнопку «Перейти на сайт»."
        )
        inline_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="Перейти на сайт", url="https://borisov.store/offer/")]]
        )
        await message.answer(answer, reply_markup=inline_kb)
        return

    if user_text == "💳 Оплата":
        answer = (
            "Мы принимаем оплату через ЮKassa — это безопасный и надёжный способ оплаты, "
            "поддерживающий банковские карты, электронные кошельки и СБП.\n\n"
            "<b>Порядок оплаты:</b>\n"
            "• Предоплата 50% перед началом работы.\n"
            "• Вторые 50% после приёмки готового сайта.\n\n"
            "Если у вас есть вопросы по другим аспектам сервиса, нажмите кнопку «Перейти на сайт»."
        )
        inline_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="Перейти на сайт", url="https://borisov.store/#pricing")]]
        )
        await message.answer(answer, reply_markup=inline_kb, parse_mode="HTML")
        return

    if user_text == "🚚 Сроки и доставка":
        answer = (
            "Стандартный срок разработки сайта — до 3 рабочих дней с момента получения предоплаты и всех материалов.\n\n"
            "В сложных случаях срок может быть увеличен до 7 рабочих дней. Подробнее — в пункте 3.7 оферты.\n\n"
            "Если у вас есть вопросы по другим аспектам сервиса, нажмите кнопку «Перейти на сайт»."
        )
        inline_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="Перейти на сайт", url="https://borisov.store/offer/")]]
        )
        await message.answer(answer, reply_markup=inline_kb)
        return

    if user_text == "🛡 Проверка самозанятого":
        answer = (
            "Исполнитель — Борисов Сергей, самозанятый, ИНН: 665200001260.\n" 
            "Проверить статус самозанятого можно через официальный сервис Федеральной налоговой службы.\n\n"
            "Для этого нажмите кнопку «Перейти на сайт» — она откроет страницу проверки."
        )
        inline_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="Перейти на сайт", url="https://npd.nalog.ru/check-status/")]]
        )
        await message.answer(answer, reply_markup=inline_kb)
        return

    if user_text == "⚡ Преимущества":
        answer = (
            "Наши преимущества помогут вам выделиться среди конкурентов и привлечь больше клиентов.\n\n"
            "Подробно о них можно узнать, нажав кнопку «Перейти на сайт» — она откроет раздел «Почему выбирают нас»."
        )
        inline_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[[types.InlineKeyboardButton(text="Перейти на сайт", url="https://borisov.store/#advantages")]]
        )
        await message.answer(answer, reply_markup=inline_kb)
        return

    if is_selfemployed_request(user_text):
        await message.answer("Выберите в меню: 🛡 Проверка самозанятого")
        return

    try:
        response = await client.chat.completions.create(
            model="google/gemini-2.5-flash-lite",
            messages=[
                {"role": "system", "content": f"{KNOWLEDGE}\n\nОтвечай без прямых ссылок. Ссылки могут быть только на кнопке «Перейти на сайт»."},
                {"role": "user", "content": user_text},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        answer = "Извините, произошла ошибка. Попробуйте ещё раз через минуту.\n\nЕсли ошибка повторяется, свяжитесь со мной через контакты на сайте."

    target_url = SITE_URL
    if is_offer_request(user_text):
        target_url = "https://borisov.store/offer/"
    else:
        target_url = BUTTON_LINKS.get(user_text, SITE_URL)

    inline_kb = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text="Перейти на сайт", url=target_url)]]
    )
    await message.answer(answer, reply_markup=inline_kb)

    if user_id not in menu_shown:
        menu_shown.add(user_id)
        await message.answer("Воспользуйтесь меню ниже:", reply_markup=main_kb)

# ========== HTTP-СЕРВЕР ДЛЯ RENDER ==========
async def handle(request):
    return web.Response(text="Bot is running")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"HTTP server started on port {PORT}")

# ========== АВТО-СБРОС WEBHOOK ==========
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
