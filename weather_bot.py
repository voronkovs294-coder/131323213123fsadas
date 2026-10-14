import os
import requests
import telebot

from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Установи токен в переменной окружения BOT_TOKEN.
# Не публикуй токен и не добавляй его в открытый репозиторий.
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "Не задан 8872120669:AAEL1gySSUn3gdonPfFb-R3XJCmhxjQEcx0. Укажи токен BotFather в переменной окружения."
    )

bot = telebot.TeleBot(TOKEN)
SUPPORT_USERNAME = "@uibgeje"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Города хранятся в памяти и сбрасываются при перезапуске программы.
user_cities = {}


def main_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.row(KeyboardButton("🌦 Погода"), KeyboardButton("👕 Что надеть"))
    menu.row(
        KeyboardButton("📅 Прогноз на 3 дня"),
        KeyboardButton("📍 Изменить город"),
    )
    menu.row(KeyboardButton("❓ Помощь"))
    return menu


def weather_description(code):
    descriptions = {
        0: "Ясно",
        1: "Преимущественно ясно",
        2: "Переменная облачность",
        3: "Пасмурно",
        45: "Туман",
        48: "Туман с изморозью",
        51: "Слабая морось",
        53: "Умеренная морось",
        55: "Сильная морось",
        56: "Ледяная морось",
        57: "Сильная ледяная морось",
        61: "Небольшой дождь",
        63: "Умеренный дождь",
        65: "Сильный дождь",
        66: "Ледяной дождь",
        67: "Сильный ледяной дождь",
        71: "Небольшой снег",
        73: "Умеренный снег",
        75: "Сильный снег",
        77: "Снежная крупа",
        80: "Небольшие ливни",
        81: "Умеренные ливни",
        82: "Сильные ливни",
        85: "Снегопад",
        86: "Сильный снегопад",
        95: "Гроза",
        96: "Гроза с градом",
        99: "Сильная гроза с градом",
    }
    return descriptions.get(code, "Неизвестные условия")


def get_city_coordinates(city):
    response = requests.get(
        GEOCODING_URL,
        params={
            "name": city,
            "count": 1,
            "language": "ru",
            "format": "json",
        },
        timeout=15,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    if not results:
        return None

    place = results[0]
    name_parts = [place["name"]]

    if place.get("admin1") and place["admin1"] != place["name"]:
        name_parts.append(place["admin1"])
    if place.get("country"):
        name_parts.append(place["country"])

    return {
        "name": ", ".join(name_parts),
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "timezone": place.get("timezone", "auto"),
    }


def get_weather(city):
    place = get_city_coordinates(city)
    if not place:
        return None

    response = requests.get(
        WEATHER_URL,
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "timezone": place["timezone"],
            "forecast_days": 3,
            "current": (
                "temperature_2m,relative_humidity_2m,"
                "apparent_temperature,precipitation,weather_code,"
                "wind_speed_10m,wind_gusts_10m"
            ),
            "daily": (
                "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,precipitation_sum"
            ),
        },
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    data["place"] = place
    return data


def get_clothing_advice(current):
    feels = current["apparent_temperature"]
    code = current["weather_code"]
    rain = current["precipitation"]
    wind = current["wind_speed_10m"]
    advice = []

    if feels < -10:
        advice.append(
            "🧥 Очень холодно: тёплая зимняя куртка, термобельё, "
            "шапка, шарф и перчатки."
        )
    elif feels < 0:
        advice.append(
            "🧥 Зимняя куртка, тёплый свитер, закрытая обувь, "
            "шапка и перчатки."
        )
    elif feels < 8:
        advice.append("🧥 Тёплая куртка или пальто, свитер и закрытая обувь.")
    elif feels < 15:
        advice.append(
            "🧥 Демисезонная куртка, лёгкий свитер или многослойная одежда."
        )
    elif feels < 22:
        advice.append(
            "👕 Лонгслив или лёгкий верхний слой; можно взять лёгкую куртку."
        )
    elif feels < 28:
        advice.append("👕 Футболка и лёгкие брюки или шорты.")
    else:
        advice.append(
            "☀️ Лёгкая, дышащая одежда и головной убор. Пей достаточно воды."
        )

    rainy_codes = {
        51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99
    }
    if code in rainy_codes or rain > 0:
        advice.append("☔ Возьми зонт или водонепроницаемую куртку.")

    if code in {71, 73, 75, 77, 85, 86}:
        advice.append("❄️ Выбирай тёплую обувь с нескользящей подошвой.")

    if wind >= 30:
        advice.append("💨 Сильный ветер: добавь ветрозащитный слой.")

    return "\n".join(advice)


def format_current(data):
    current = data["current"]
    place = data["place"]
    return (
        f"🌦 Погода: {place['name']}\n\n"
        f"🌡 Температура: {current['temperature_2m']} °C\n"
        f"🤔 Ощущается как: {current['apparent_temperature']} °C\n"
        f"🌤 Условия: {weather_description(current['weather_code'])}\n"
        f"💧 Влажность: {current['relative_humidity_2m']}%\n"
        f"💨 Ветер: {current['wind_speed_10m']} км/ч\n"
        f"🌬 Порывы ветра: {current['wind_gusts_10m']} км/ч\n"
        f"🌧 Осадки сейчас: {current['precipitation']} мм\n"
        f"🕒 Время наблюдения: {current['time']}"
    )


def format_forecast(data):
    daily = data["daily"]
    lines = [f"📅 Прогноз: {data['place']['name']}\n"]

    for i, date in enumerate(daily["time"]):
        description = weather_description(daily["weather_code"][i])
        rain_chance = daily["precipitation_probability_max"][i]
        rain_sum = daily["precipitation_sum"][i]
        lines.append(
            f"\n📆 {date}\n"
            f"🌤 {description}\n"
            f"🌡 {daily['temperature_2m_min'][i]}…"
            f"{daily['temperature_2m_max'][i]} °C\n"
            f"🌧 Вероятность осадков: {rain_chance}%\n"
            f"💧 Ожидаемые осадки: {rain_sum} мм"
        )

    return "\n".join(lines)


def send_weather(message, mode):
    city = user_cities.get(message.from_user.id)
    if not city:
        bot.send_message(
            message.chat.id,
            "📍 Сначала напиши название своего города, например: Вена.",
            reply_markup=main_menu(),
        )
        return

    try:
        data = get_weather(city)
        if not data:
            bot.send_message(
                message.chat.id,
                "Не нашёл этот город. Нажми «📍 Изменить город» и попробуй ещё раз.",
                reply_markup=main_menu(),
            )
            return

        if mode == "weather":
            text = format_current(data)
        elif mode == "clothes":
            text = (
                format_current(data)
                + "\n\n👕 Что надеть:\n"
                + get_clothing_advice(data["current"])
            )
        else:
            text = format_forecast(data)

        bot.send_message(message.chat.id, text, reply_markup=main_menu())

    except requests.RequestException:
        bot.send_message(
            message.chat.id,
            "⚠️ Не удалось получить погоду. Проверь интернет и попробуй позже.",
            reply_markup=main_menu(),
        )
    except (KeyError, IndexError, TypeError, ValueError):
        bot.send_message(
            message.chat.id,
            "⚠️ Не удалось обработать данные погоды. Попробуй позже.",
            reply_markup=main_menu(),
        )


@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привет! 👋 Я бот «Погода и одежда».\n\n"
        "🌦 Покажу текущую погоду.\n"
        "👕 Подскажу, что надеть.\n"
        "📅 Покажу прогноз на 3 дня.\n\n"
        "Для начала напиши название своего города.",
        reply_markup=main_menu(),
    )


@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "📋 Команды:\n\n"
        "/start — главное меню\n"
        "/help — помощь\n"
        "/weather — текущая погода\n"
        "/clothes — рекомендации по одежде\n"
        "/forecast — прогноз на 3 дня\n"
        "/city — изменить город\n\n"
        "Также можно пользоваться кнопками меню.",
        reply_markup=main_menu(),
    )


@bot.message_handler(commands=["city"])
def city_command(message):
    bot.send_message(
        message.chat.id,
        "📍 Напиши название нового города.",
        reply_markup=main_menu(),
    )


@bot.message_handler(commands=["weather"])
def weather_command(message):
    send_weather(message, "weather")


@bot.message_handler(commands=["clothes"])
def clothes_command(message):
    send_weather(message, "clothes")


@bot.message_handler(commands=["forecast"])
def forecast_command(message):
    send_weather(message, "forecast")


@bot.message_handler(func=lambda m: m.text == "🌦 Погода")
def weather_button(message):
    send_weather(message, "weather")


@bot.message_handler(func=lambda m: m.text == "👕 Что надеть")
def clothes_button(message):
    send_weather(message, "clothes")


@bot.message_handler(func=lambda m: m.text == "📅 Прогноз на 3 дня")
def forecast_button(message):
    send_weather(message, "forecast")


@bot.message_handler(func=lambda m: m.text == "📍 Изменить город")
def change_city_button(message):
    city_command(message)


@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_button(message):
    help_command(message)


@bot.message_handler(content_types=["text"])
def handle_city(message):
    city = message.text.strip()

    if not city or len(city) > 100:
        bot.send_message(message.chat.id, "Введи корректное название города.")
        return

    try:
        place = get_city_coordinates(city)
        if not place:
            bot.send_message(
                message.chat.id,
                "❌ Город не найден. Попробуй другое название.",
                reply_markup=main_menu(),
            )
            return

        user_cities[message.from_user.id] = city
        bot.send_message(
            message.chat.id,
            f"✅ Город выбран: {place['name']}\n"
            "Теперь нажми «🌦 Погода» или «👕 Что надеть».",
            reply_markup=main_menu(),
        )

    except requests.RequestException:
        bot.send_message(
            message.chat.id,
            "⚠️ Не удалось проверить город. Попробуй позже.",
            reply_markup=main_menu(),
        )


if __name__ == "__main__":
    print("Бот погоды запущен!")
    bot.infinity_polling(skip_pending=True)
