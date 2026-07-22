from datetime import datetime, timedelta
from database import connect


WORK_START = "09:00"
WORK_END = "17:00"


def get_work_times():

    times = []

    current = datetime.strptime(
        WORK_START,
        "%H:%M"
    )

    end = datetime.strptime(
        WORK_END,
        "%H:%M"
    )


    while current < end:

        times.append(
            current.strftime("%H:%M")
        )

        current += timedelta(minutes=30)


    return times



def get_free_times(date, exclude_booking_id=None):

    all_times = get_work_times()


    conn = connect()
    cursor = conn.cursor()


    query = """
        SELECT time, duration
        FROM bookings
        WHERE date = ?
    """
    parameters = [date]

    if exclude_booking_id is not None:
        query += " AND id != ?"
        parameters.append(exclude_booking_id)

    cursor.execute(query, parameters)


    bookings = cursor.fetchall()

    conn.close()



    busy_times = []


    for booking_time, duration in bookings:

        start_time = datetime.strptime(
            booking_time,
            "%H:%M"
        )


        for minute in range(
            0,
            duration,
            30
        ):

            busy_times.append(
                (
                    start_time 
                    + timedelta(minutes=minute)
                ).strftime("%H:%M")
            )



    free_times = []


    for time in all_times:

        if time not in busy_times:

            free_times.append(time)


    return free_times