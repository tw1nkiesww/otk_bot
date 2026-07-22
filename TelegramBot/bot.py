from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import asyncio
from datetime import datetime, timedelta

from database import (
    create_table,
    add_booking,
    get_all_bookings,
    get_client_bookings,
    get_client_booking,
    get_client_history,
    get_booking_statistics,
    get_due_reminders,
    mark_reminder_sent,
    delete_booking,
    update_client_booking
)
from scheduler import get_free_times


TOKEN = "8701512386:AAHQWYJ4Qt0JT632ABG_BDYwmaVGMx-zzIM"

ADMIN_ID = 5430519340


bot = Bot(token=TOKEN)
dp = Dispatcher()

ADMIN_PANEL_TEXT = """
👨‍💼 Привет здоровяяяк

Тут ви можете повністю керувати записами клієнтів.

━━━━━━━━━━━━━━━━━━━━

📋 Переглянути записи
• Відображає всі записи, які є в базі даних.
• Для кожного запису показуються:
    — ID
    — Тип транспорту
    — Ім'я клієнта
    — Телефон
    — Державний номер
    — Дата
    — Час
    — Тривалість перевірки

━━━━━━━━━━━━━━━━━━━━

➕ Додати запис
• Дозволяє вручну створити запис.
• Використовуйте, якщо клієнт записується телефоном або особисто.

━━━━━━━━━━━━━━━━━━━━

🗑 Видалити запис
• Видаляє запис із бази даних.
• Для видалення необхідно ввести ID потрібного запису.

━━━━━━━━━━━━━━━━━━━━

📊 Статистика
Дозволяє швидко переглянути кількість записів за різні періоди.

Відображається:

📅 За поточний тиждень
• Кількість записів, створених за поточний календарний тиждень.

🗓 За місяць
• Кількість записів за поточний місяць (із зазначенням місяця та року).

📈 За весь час
• Загальна кількість записів, створених з моменту початку роботи бота.

━━━━━━━━━━━━━━━━━━━━

Статистика оновлюється автоматично після кожного нового або видаленого запису.

━━━━━━━━━━━━━━━━━━━━

⬅️ Назад
• Вихід із панелі адміністратора.
• Повернення до головного меню.

━━━━━━━━━━━━━━━━━━━━

⚠️ Увага!

Перед видаленням запису уважно перевіряйте його ID.

Видалений запис відновити неможливо.
"""


# Главное меню
def get_menu(user_id):

    # Если это администратор
    if user_id == ADMIN_ID:

        return ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="⚙️ Панель адм")
                ]
            ],
            resize_keyboard=True
        )


    # Если обычный клиент

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🚗 Записатися на ОТК")
            ],
            [
                KeyboardButton(text="📅 Перенос запису")
            ],
            [
                KeyboardButton(text="📜 Історія клієнта")
            ],
            [
                KeyboardButton(text="📞 Зв'язатися з нами")
            ]
        ],
        resize_keyboard=True
    )

back_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="⬅️ Назад")
        ]
    ],
    resize_keyboard=True
)

admin_panel_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📋 Переглянути записи")
        ],
            [
                KeyboardButton(text="📊 Статистика")
            ],
        [
            KeyboardButton(text="➕ Додати запис")
        ],
        [
            KeyboardButton(text="🗑 Видалити запис")
        ],
        [
            KeyboardButton(text="⬅️ Назад")
        ]
    ],
    resize_keyboard=True
)

# Выбор транспорта
transport_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🏍️ Мотоцикл")
        ],
        [
            KeyboardButton(text="🚗 Легковий автомобіль")
        ],
        [
            KeyboardButton(text="🚛 Вантажний автомобіль (тягач)")
        ],
        [
            KeyboardButton(text="🚚 Вантажний автомобіль з причепом")
        ],
        [
            KeyboardButton(text="🚌 Автобус")
        ],
        [
            KeyboardButton(text="⬅️ Назад")
        ]
    ],
    resize_keyboard=True
)
# Кнопки дат
def date_keyboard():

    dates = []

    today = datetime.now()

    current = today

    while len(dates) < 5:

        if current.weekday() < 5:

            dates.append(
                current.strftime("%d.%m")
            )

        current += timedelta(days=1)

    keyboard = [
        [KeyboardButton(text=f"📅 {date}")]
        for date in dates
    ]

    keyboard.append(
        [KeyboardButton(text="⬅️ Назад")]
    )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )



# Кнопки времени
def time_keyboard(times):

    buttons = []

    for time in times:
        buttons.append(
            [
                KeyboardButton(text=time)
            ]
        )

    buttons.append(
        [
            KeyboardButton(text="⬅️ Назад")
        ]
    )

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


def reschedule_keyboard(bookings):
    buttons = []

    for booking_id, _, date, time, _ in bookings:
        buttons.append(
            [KeyboardButton(text=f"🔁 №{booking_id} — {date} о {time}")]
        )

    buttons.append(
        [KeyboardButton(text="⬅️ Назад")]
    )

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )


class Booking(StatesGroup):

    transport = State()
    name = State()
    phone = State()
    car = State()
    number = State()
    date = State()
    time = State()

    admin_transport = State()
    admin_name = State()
    admin_phone = State()
    admin_car = State()
    admin_number = State()
    admin_date = State()
    admin_time = State()

    delete_booking = State()

    reschedule_booking = State()
    reschedule_date = State()
    reschedule_time = State()


@dp.message(lambda message: message.text == "⬅️ Назад")
async def back_handler(message: types.Message, state: FSMContext):

    current_state = await state.get_state()

    if current_state is None and message.from_user.id == ADMIN_ID:
        await message.answer(
            "⚙️ Ви вже в панелі адміністратора.",
            reply_markup=admin_panel_menu
        )
        return

    # ===== КЛИЕНТ =====

    if current_state == Booking.transport:
        await state.clear()

        await message.answer(
            "❌ Запис скасовано.",
            reply_markup=get_menu(message.from_user.id)
        )
        return


    elif current_state == Booking.name:
        await state.set_state(Booking.transport)

        await message.answer(
            "Оберіть тип транспортного засобу:",
            reply_markup=transport_menu
        )
        return


    elif current_state == Booking.phone:
        await state.set_state(Booking.name)

        await message.answer(
            "Введіть ваше ім'я:",
            reply_markup=back_menu
        )
        return


    elif current_state == Booking.car:
        await state.set_state(Booking.phone)

        await message.answer(
            "Введіть номер телефону:",
            reply_markup=back_menu
        )
        return


    elif current_state == Booking.number:
        await state.set_state(Booking.car)

        await message.answer(
            "Введіть марку та модель транспортного засобу:",
            reply_markup=back_menu
        )
        return


    elif current_state == Booking.date:
        await state.set_state(Booking.number)

        await message.answer(
            "Введіть державний номер:",
            reply_markup=back_menu
        )
        return


    elif current_state == Booking.time:
        await state.set_state(Booking.date)

        await message.answer(
            "Оберіть дату:",
            reply_markup=date_keyboard()
        )
        return



    # ===== АДМИН =====


    elif current_state == Booking.admin_transport:
        await state.clear()

        await message.answer(
            ADMIN_PANEL_TEXT,
            reply_markup=admin_panel_menu
        )
        return


    elif current_state == Booking.admin_name:
        await state.set_state(Booking.admin_transport)

        await message.answer(
            "Оберіть тип транспорту:",
            reply_markup=transport_menu
        )
        return


    elif current_state == Booking.admin_phone:
        await state.set_state(Booking.admin_name)

        await message.answer(
            "Введіть ім'я клієнта:"
        )
        return


    elif current_state == Booking.admin_car:
        await state.set_state(Booking.admin_phone)

        await message.answer(
            "Введіть номер телефону клієнта:"
        )
        return


    elif current_state == Booking.admin_number:
        await state.set_state(Booking.admin_car)

        await message.answer(
            "Введіть марку та модель:"
        )
        return


    elif current_state == Booking.admin_date:
        await state.set_state(Booking.admin_number)

        await message.answer(
            "Введіть державний номер:"
        )
        return


    elif current_state == Booking.admin_time:
        await state.set_state(Booking.admin_date)

        await message.answer(
            "Оберіть дату:",
            reply_markup=date_keyboard()
        )
        return


    elif current_state == Booking.delete_booking:
        await state.clear()

        await message.answer(
            ADMIN_PANEL_TEXT,
            reply_markup=admin_panel_menu
        )
        return


    elif current_state == Booking.reschedule_booking:
        await state.clear()

        await message.answer(
            "Головне меню:",
            reply_markup=get_menu(message.from_user.id)
        )
        return


    elif current_state == Booking.reschedule_date:
        bookings = get_client_bookings(message.from_user.id)
        await state.set_state(Booking.reschedule_booking)

        await message.answer(
            "Оберіть запис для перенесення:",
            reply_markup=reschedule_keyboard(bookings)
        )
        return


    elif current_state == Booking.reschedule_time:
        await state.set_state(Booking.reschedule_date)

        await message.answer(
            "Оберіть нову дату:",
            reply_markup=date_keyboard()
        )
        return



@dp.message(Command("start"))
async def start(message: types.Message):

    if message.from_user.id == ADMIN_ID:
        await message.answer(
            ADMIN_PANEL_TEXT,
            reply_markup=admin_panel_menu
        )
        return

    await message.answer_photo(
    photo="AgACAgIAAxkBAAICxmpec1rXKFB3DfrBV8Vr3V8Zaf3AAAKXHGsbB3PxSr578PVJ1i1pAQADAgADeQADPQQ",
    caption="""
👋 Ласкаво просимо!
🚗 OTK Odesa Baltskaya Lab 749

Сервіс обов'язкового технічного контролю транспортних засобів.

━━━━━━━━━━━━━━━━━━━━

📍 Адреса:
Балтська дорога, 1
Одеса, Одеська область, 65000

🕒 Графік роботи:
Пн-Пт: 09:00 — 18:00

📞 Телефон:
+38 (050) 603 33 49
+38 (067) 102 54 24
+38 (067) 650 15 21

━━━━━━━━━━━━━━━━━━━━

📄 Для проходження тех.огляду необхідно мати при собі:

• Технічний паспорт
• Посвідчення водія
• Аптечку
• Вогнегасник
• Знак аварійної зупинки

━━━━━━━━━━━━━━━━━━━━

💰 Вартість послуг:

🏍️ Мотоцикл — 4300 грн

🚗 Автомобілі до 3.5 тон — 4300 грн

🚗 Автомобілі від 3.5 до 12 тон — 4700 грн

🚚 Вантажні автомобілі понад 12 тон — 4900 грн

🚌 Автобуси з повною масою до 5 тон — 4700 грн

🚌 Автобуси більше 8 місць — 4900 грн

━━━━━━━━━━━━━━━━━━━━

Натисніть кнопку нижче, щоб записатися.
""",
    reply_markup=get_menu(message.from_user.id)
)



@dp.message(lambda message: message.text == "📞 Зв'язатися з нами")
async def contact(message: types.Message):

    await message.answer(
        """
@dp.message(lambda message: message.text == "📜 Історія клієнта")
async def client_history(message: types.Message, state: FSMContext):

    await state.clear()
    history = get_client_history(message.from_user.id)

    if not history:
        await message.answer(
            "У вас ще немає записів на ОТК.",
            reply_markup=get_menu(message.from_user.id)
        )
        return

    history_lines = [
        f"• {date}.{datetime.now().year}"
        for date, _, _ in history
    ]

    await message.answer(
        "🚗 Ви проходили ОТК:\n\n" + "\n".join(history_lines),
        reply_markup=get_menu(message.from_user.id)
    )


@dp.message(lambda message: message.text == "📅 Перенос запису")
async def reschedule_start(message: types.Message, state: FSMContext):

    bookings = get_client_bookings(message.from_user.id)

    if not bookings:
        await message.answer(
            "У вас немає записів, які можна перенести.",
            reply_markup=get_menu(message.from_user.id)
        )
        return

    await state.set_state(Booking.reschedule_booking)
    await message.answer(
        "Оберіть запис для перенесення:",
        reply_markup=reschedule_keyboard(bookings)
    )


@dp.message(Booking.reschedule_booking)
async def reschedule_booking_select(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    try:
        booking_id = int(message.text.split("№", 1)[1].split(" ", 1)[0])
    except (IndexError, ValueError):
        await message.answer("Оберіть запис за допомогою кнопки нижче.")
        return

    booking = get_client_booking(message.from_user.id, booking_id)

    if booking is None:
        await message.answer("❌ Запис не знайдено. Оберіть запис зі списку.")
        return

    await state.update_data(booking_id=booking_id)
    await state.set_state(Booking.reschedule_date)
    await message.answer(
        "Оберіть нову дату:",
        reply_markup=date_keyboard()
    )


@dp.message(Booking.reschedule_date)
async def reschedule_date_select(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    date = message.text.replace("📅 ", "")
    data = await state.get_data()
    free_times = get_free_times(date, exclude_booking_id=data["booking_id"])

    if not free_times:
        await message.answer(
            "❌ На цю дату немає вільного часу. Оберіть іншу дату.",
            reply_markup=date_keyboard()
        )
        return

    await state.update_data(date=date)
    await state.set_state(Booking.reschedule_time)
    await message.answer(
        "Оберіть новий час:",
        reply_markup=time_keyboard(free_times)
    )


@dp.message(Booking.reschedule_time)
async def reschedule_time_select(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    data = await state.get_data()
    updated = update_client_booking(
        message.from_user.id,
        data["booking_id"],
        data["date"],
        message.text
    )

    if not updated:
        await state.clear()
        await message.answer(
            "❌ Не вдалося перенести запис.",
            reply_markup=get_menu(message.from_user.id)
        )
        return

    await state.clear()
    await message.answer(
        f"✅ Запис перенесено на {data['date']} о {message.text}.",
        reply_markup=get_menu(message.from_user.id)
    )


📞 Зв'язатися з нами

Якщо у вас залишилися питання,
телефонуйте за номером:

📞 +38 (050) 603 33 49

Будемо раді допомогти!
        """
    )



@dp.message(lambda message: message.text == "🚗 Записатися на ОТК")
async def booking_start(message: types.Message, state: FSMContext):

    await message.answer(
        "Оберіть тип транспортного засобу:",
        reply_markup=transport_menu
    )

    await state.set_state(Booking.transport)



@dp.message(Booking.transport)
async def get_transport(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return


    await state.update_data(
        transport=message.text
    )


    await message.answer(
        "Введіть ваше ім'я:",
        reply_markup=back_menu
    )


    await state.set_state(Booking.name)


@dp.message(Booking.name)
async def get_name(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        name=message.text
    )

    await message.answer(
    "Введіть номер телефону:",
    reply_markup=back_menu
)

    await state.set_state(Booking.phone)



@dp.message(Booking.phone)
async def get_phone(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        phone=message.text
    )

    await message.answer(
    "Введіть марку та модель транспортного засобу:",
    reply_markup=back_menu
)

    await state.set_state(Booking.car)



@dp.message(Booking.car)
async def get_car(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        car=message.text
    )

    await message.answer(
    "Введіть державний номер:",
    reply_markup=back_menu
)

    await state.set_state(Booking.number)



@dp.message(Booking.number)
async def get_number(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        number=message.text
    )

    await message.answer(
        "Оберіть дату:",
        reply_markup=date_keyboard()
    )

    await state.set_state(Booking.date)



@dp.message(Booking.date)
async def get_date(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    date = message.text.replace("📅 ", "")

    await state.update_data(
        date=date
    )

    free_times = get_free_times(date)


    if not free_times:

        await message.answer(
            "❌ На цю дату немає вільного часу. Оберіть іншу дату."
        )

        return


    await message.answer(
        "Оберіть вільний час:",
        reply_markup=time_keyboard(free_times)
    )

    await state.set_state(Booking.time)



@dp.message(Booking.time)
async def get_time(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        time=message.text
    )

    data = await state.get_data()


    # Визначаємо тривалість перевірки

    if data["transport"] == "🏍️ Мотоцикл":
        duration = 30

    elif data["transport"] == "🚗 Легковий автомобіль":
        duration = 30

    elif data["transport"] == "🚛 Вантажний автомобіль (тягач)":
        duration = 60

    elif data["transport"] == "🚚 Вантажний автомобіль з причепом":
        duration = 120

    elif data["transport"] == "🚌 Автобус":
        duration = 60

    else:
        duration = 30



    # Запис у базу

    add_booking(
        data["transport"],
        data["name"],
        data["phone"],
        data["number"],
        data["date"],
        data["time"],
        duration,
        user_id=message.from_user.id
    )



    # Повідомлення адміну

    await bot.send_message(
        ADMIN_ID,
        f"""
🔔 Нова заявка ОТК


🚘 Тип транспорту:
{data['transport']}


👤 Клієнт:
{data['name']}


📞 Телефон:
{data['phone']}


🚗 Марка та модель:
{data['car']}


🔢 Державний номер:
{data['number']}


📅 Дата:
{data['date']}


🕒 Час:
{data['time']}


⏱ Тривалість:
{duration} хв.
"""
    )



    await message.answer(
        """
✅ Заявку успішно відправлено!

Дякуємо за звернення до:

🚗 OTK Odesa Baltskaya Lab 749

📞 Для підтвердження запису з вами зв'яжеться наш менеджер.

Очікуйте дзвінка.
        """,
        reply_markup=get_menu(message.from_user.id)
    )


    await state.clear()


@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text == "⚙️ Панель адм")
async def open_admin_panel(message: types.Message):

    await message.answer(
        ADMIN_PANEL_TEXT,
        reply_markup=admin_panel_menu
    )


# =========================
# ПРОСМОТР ЗАПИСЕЙ
# =========================

@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text == "📋 Переглянути записи")
async def view_bookings(message: types.Message, state: FSMContext):

    await state.clear()

    bookings = get_all_bookings()

    if not bookings:
        await message.answer(
            "📋 Записів поки немає.",
            reply_markup=admin_panel_menu
        )
        return


    text = "📋 Усі записи ОТК:\n\n"


    for booking in bookings:

        text += f"""
Запис №{booking[0]}

🚘 Транспорт:
{booking[1]}

👤 Клієнт:
{booking[2]}

📞 Телефон:
{booking[3]}

🔢 Номер:
{booking[4]}

📅 Дата:
{booking[5]}

🕒 Час:
{booking[6]}

⏱ Тривалість:
{booking[7]} хв.

━━━━━━━━━━━━
"""


    await message.answer(
        text,
        reply_markup=admin_panel_menu
    )


# =========================
# СТАТИСТИКА
# =========================

@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text == "📊 Статистика")
async def view_statistics(message: types.Message, state: FSMContext):

    await state.clear()

    statistics = get_booking_statistics()
    current_month = datetime.now().strftime("%m.%Y")
    transport_statistics = "\n".join(
        f"🚗 {transport}: {count}"
        for transport, count in statistics["transport_counts"]
    ) or "Немає даних"

    await message.answer(
        f"""
📊 Статистика записів

📅 За поточний тиждень: {statistics['weekly']}

🗓 За місяць ({current_month}): {statistics['monthly']}

📈 За весь час: {statistics['total']}

🚗 За типами транспорту:
{transport_statistics}

📅 Записів сьогодні: {statistics['today']}

📈 Середня кількість записів за день: {statistics['average_daily']}

🕒 Найпопулярніший час: {statistics['popular_time']}

📆 Найзавантаженіший день тижня: {statistics['popular_weekday']}
        """,
        reply_markup=admin_panel_menu
    )



# =========================
# ДОБАВЛЕНИЕ ЗАПИСИ АДМИНОМ
# =========================

@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text == "➕ Додати запис")
async def admin_add_start(message: types.Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "Оберіть тип транспорту:",
        reply_markup=transport_menu
    )

    await state.set_state(Booking.admin_transport)



@dp.message(Booking.admin_transport)
async def admin_get_transport(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        transport=message.text
    )

    await message.answer(
        "Введіть ім'я клієнта:",
        reply_markup=back_menu
    )

    await state.set_state(Booking.admin_name)



@dp.message(Booking.admin_name)
async def admin_get_name(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        name=message.text
    )

    await message.answer(
        "Введіть номер телефону клієнта:",
        reply_markup=back_menu
    )

    await state.set_state(Booking.admin_phone)



@dp.message(Booking.admin_phone)
async def admin_get_phone(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        phone=message.text
    )

    await message.answer(
        "Введіть марку та модель транспортного засобу:",
        reply_markup=back_menu
    )

    await state.set_state(Booking.admin_car)



@dp.message(Booking.admin_car)
async def admin_get_car(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        car=message.text
    )

    await message.answer(
        "Введіть державний номер:",
        reply_markup=back_menu
    )

    await state.set_state(Booking.admin_number)



@dp.message(Booking.admin_number)
async def admin_get_number(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        number=message.text
    )

    await message.answer(
        "Оберіть дату:",
        reply_markup=date_keyboard()
    )

    await state.set_state(Booking.admin_date)



@dp.message(Booking.admin_date)
async def admin_get_date(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    date = message.text.replace("📅 ", "")

    await state.update_data(
        date=date
    )


    free_times = get_free_times(date)


    if not free_times:

        await message.answer(
            "❌ На цю дату немає вільного часу."
        )

        return


    await message.answer(
        "Оберіть час:",
        reply_markup=time_keyboard(free_times)
    )

    await state.set_state(Booking.admin_time)



@dp.message(Booking.admin_time)
async def admin_get_time(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    await state.update_data(
        time=message.text
    )

    data = await state.get_data()


    if data["transport"] == "🏍️ Мотоцикл":
        duration = 30

    elif data["transport"] == "🚗 Легковий автомобіль":
        duration = 30

    elif data["transport"] == "🚛 Вантажний автомобіль (тягач)":
        duration = 60

    elif data["transport"] == "🚚 Вантажний автомобіль з причепом":
        duration = 120

    elif data["transport"] == "🚌 Автобус":
        duration = 60

    else:
        duration = 30


    add_booking(
        data["transport"],
        data["name"],
        data["phone"],
        data["number"],
        data["date"],
        data["time"],
        duration
    )


    await message.answer(
        "✅ Запис успішно додано!",
        reply_markup=admin_panel_menu
    )


    await state.clear()



# =========================
# УДАЛЕНИЕ ЗАПИСИ
# =========================

@dp.message(lambda message: message.from_user.id == ADMIN_ID and message.text == "🗑 Видалити запис")
async def delete_start(message: types.Message, state: FSMContext):

    await state.clear()

    await message.answer(
        "Введіть ID запису для видалення:",
        reply_markup=back_menu
    )

    await state.set_state(Booking.delete_booking)



@dp.message(Booking.delete_booking)
async def delete_booking_handler(message: types.Message, state: FSMContext):

    if message.text == "⬅️ Назад":
        await back_handler(message, state)
        return

    try:
        booking_id = int(message.text)

    except ValueError:

        await message.answer(
            "❌ Введіть тільки число ID."
        )

        return


    result = delete_booking(booking_id)


    if result:

        await message.answer(
            "✅ Запис видалено.",
            reply_markup=admin_panel_menu
        )

    else:

        await message.answer(
            "❌ Запис не знайдено.",
            reply_markup=admin_panel_menu
        )


    await state.clear()


@dp.message(lambda message: message.photo)
async def get_photo_id(message: types.Message):

    photo_id = message.photo[-1].file_id

    await message.answer(
        f"ID фото:\n\n{photo_id}"
    )




async def reminders_worker():
    while True:
        now = datetime.now()

        try:
            reminders = get_due_reminders(now)

            for reminder in reminders:
                time_left = reminder["appointment"] - now

                if (
                    not reminder["day_sent"]
                    and timedelta(hours=1) < time_left <= timedelta(days=1)
                ):
                    await bot.send_message(
                        reminder["user_id"],
                        f"🔔 Нагадуємо, що завтра у вас запис на ОТК о {reminder['time']}."
                    )
                    mark_reminder_sent(reminder["id"], "day")
                    continue

                if (
                    not reminder["hour_sent"]
                    and timedelta(0) < time_left <= timedelta(hours=1)
                ):
                    await bot.send_message(
                        reminder["user_id"],
                        f"🔔 Нагадуємо, що через годину у вас запис на ОТК о {reminder['time']}."
                    )
                    mark_reminder_sent(reminder["id"], "hour")

        except Exception as error:
            print(f"Помилка нагадувань: {error}")

        await asyncio.sleep(60)


async def main():

    create_table()

    print("Бот запущено!")

    reminders_task = asyncio.create_task(reminders_worker())

    try:
        await dp.start_polling(bot)
    finally:
        reminders_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())