import sqlite3
from collections import Counter
from datetime import datetime, timedelta

DB_NAME = "database.db"


def connect():
    return sqlite3.connect(DB_NAME)


def create_table():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transport TEXT,
        name TEXT,
        phone TEXT,
        plate TEXT,
        date TEXT,
        time TEXT,
        duration INTEGER,
        user_id INTEGER,
        day_reminder_sent INTEGER NOT NULL DEFAULT 0,
        hour_reminder_sent INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("PRAGMA table_info(bookings)")
    columns = {row[1] for row in cursor.fetchall()}

    if "user_id" not in columns:
        cursor.execute("ALTER TABLE bookings ADD COLUMN user_id INTEGER")

    if "day_reminder_sent" not in columns:
        cursor.execute(
            "ALTER TABLE bookings ADD COLUMN day_reminder_sent INTEGER NOT NULL DEFAULT 0"
        )

    if "hour_reminder_sent" not in columns:
        cursor.execute(
            "ALTER TABLE bookings ADD COLUMN hour_reminder_sent INTEGER NOT NULL DEFAULT 0"
        )

    conn.commit()
    conn.close()
def add_booking(transport, name, phone, plate, date, time, duration, user_id=None):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO bookings
        (transport, name, phone, plate, date, time, duration, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (transport, name, phone, plate, date, time, duration, user_id)
    )

    conn.commit()
    conn.close()


def get_all_bookings():

    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
        id,
        transport,
        name,
        phone,
        plate,
        date,
        time,
        duration
        FROM bookings
        ORDER BY date, time
        """
    )

    bookings = cursor.fetchall()

    conn.close()

    return bookings


def get_client_bookings(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, transport, date, time, duration
        FROM bookings
        WHERE user_id = ?
        ORDER BY date, time
        """,
        (user_id,)
    )
    bookings = cursor.fetchall()
    conn.close()

    return bookings


def get_client_booking(user_id, booking_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, transport, date, time, duration
        FROM bookings
        WHERE id = ? AND user_id = ?
        """,
        (booking_id, user_id)
    )
    booking = cursor.fetchone()
    conn.close()

    return booking


def update_client_booking(user_id, booking_id, date, time):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE bookings
        SET date = ?, time = ?, day_reminder_sent = 0, hour_reminder_sent = 0
        WHERE id = ? AND user_id = ?
        """,
        (date, time, booking_id, user_id)
    )
    updated = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return updated


def get_client_history(user_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT date, time, created_at
        FROM bookings
        WHERE user_id = ?
        ORDER BY created_at
        """,
        (user_id,)
    )
    history = cursor.fetchall()
    conn.close()

    return history


def get_booking_statistics():
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(
                CASE WHEN strftime('%Y-%W', created_at, 'localtime') =
                          strftime('%Y-%W', 'now', 'localtime')
                     THEN 1 ELSE 0 END
            ), 0),
            COALESCE(SUM(
                CASE WHEN strftime('%Y-%m', created_at, 'localtime') =
                          strftime('%Y-%m', 'now', 'localtime')
                     THEN 1 ELSE 0 END
            ), 0)
        FROM bookings
        """
    )

    total, weekly, monthly = cursor.fetchone()

    cursor.execute(
        """
        SELECT transport, COUNT(*)
        FROM bookings
        GROUP BY transport
        ORDER BY COUNT(*) DESC, transport
        """
    )
    transport_counts = cursor.fetchall()

    cursor.execute(
        """
        SELECT date, time, created_at
        FROM bookings
        """
    )
    booking_rows = cursor.fetchall()
    conn.close()

    today = datetime.now()
    today_text = today.strftime("%d.%m")
    today_count = sum(1 for booking_date, _, _ in booking_rows if booking_date == today_text)

    created_dates = {created_at[:10] for _, _, created_at in booking_rows if created_at}
    average_daily = round(total / len(created_dates), 2) if created_dates else 0

    time_counts = Counter(booking_time for _, booking_time, _ in booking_rows if booking_time)
    popular_time = time_counts.most_common(1)[0][0] if time_counts else "Немає даних"

    weekday_counts = Counter()
    for booking_date, _, _ in booking_rows:
        try:
            scheduled_date = datetime.strptime(
                f"{booking_date}.{today.year}",
                "%d.%m.%Y"
            )
        except (TypeError, ValueError):
            continue

        weekday_counts[scheduled_date.weekday()] += 1

    weekday_names = (
        "Понеділок",
        "Вівторок",
        "Середа",
        "Четвер",
        "П'ятниця",
        "Субота",
        "Неділя"
    )
    popular_weekday = (
        weekday_names[weekday_counts.most_common(1)[0][0]]
        if weekday_counts else "Немає даних"
    )

    return {
        "total": total,
        "weekly": weekly,
        "monthly": monthly,
        "transport_counts": transport_counts,
        "today": today_count,
        "average_daily": average_daily,
        "popular_time": popular_time,
        "popular_weekday": popular_weekday
    }


def get_due_reminders(now):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, user_id, name, date, time, day_reminder_sent, hour_reminder_sent
        FROM bookings
        WHERE user_id IS NOT NULL
        """
    )
    bookings = cursor.fetchall()
    conn.close()

    due = []
    for booking in bookings:
        booking_id, user_id, name, date, time, day_sent, hour_sent = booking
        try:
            appointment = datetime.strptime(
                f"{date}.{now.year} {time}",
                "%d.%m.%Y %H:%M"
            )
        except (TypeError, ValueError):
            continue

        if appointment < now - timedelta(days=1):
            appointment = appointment.replace(year=now.year + 1)

        due.append({
            "id": booking_id,
            "user_id": user_id,
            "name": name,
            "date": date,
            "time": time,
            "appointment": appointment,
            "day_sent": bool(day_sent),
            "hour_sent": bool(hour_sent)
        })

    return due


def mark_reminder_sent(booking_id, reminder_type):
    column = {
        "day": "day_reminder_sent",
        "hour": "hour_reminder_sent"
    }.get(reminder_type)

    if column is None:
        raise ValueError("Unknown reminder type")

    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE bookings SET {column} = 1 WHERE id = ?",
        (booking_id,)
    )
    conn.commit()
    conn.close()



def delete_booking(booking_id):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM bookings WHERE id = ?",
        (booking_id,)
    )

    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted > 0