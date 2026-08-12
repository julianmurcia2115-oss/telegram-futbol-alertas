import os
import requests
from datetime import datetime, timezone

API_KEY = os.environ["API_FOOTBALL_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

API_URL = "https://v3.football.api-sports.io"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

HEADERS = {
    "x-apisports-key": API_KEY
}


def telegram(method, params=None):
    response = requests.post(
        f"{TELEGRAM_URL}/{method}",
        data=params or {},
        timeout=30
    )
    return response.json()


def send_message(chat_id, text):
    telegram("sendMessage", {
        "chat_id": chat_id,
        "text": text
    })


def get_chat_id():
    data = telegram("getUpdates")

    if not data.get("ok"):
        print("Error obteniendo mensajes de Telegram:", data)
        return None

    updates = data.get("result", [])

    if not updates:
        return None

    for update in reversed(updates):
        message = update.get("message")

        if message:
            return message["chat"]["id"]

    return None


def get_today_fixtures():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    response = requests.get(
        f"{API_URL}/fixtures",
        headers=HEADERS,
        params={"date": today},
        timeout=30
    )

    response.raise_for_status()
    return response.json().get("response", [])


def get_team_last_19(team_id):
    response = requests.get(
        f"{API_URL}/fixtures",
        headers=HEADERS,
        params={
            "team": team_id,
            "last": 19
        },
        timeout=30
    )

    response.raise_for_status()
    return response.json().get("response", [])


def calculate_btts(fixtures, team_id):
    total = 0
    btts = 0
    scored = 0
    conceded = 0

    for fixture in fixtures:
        home_id = fixture["teams"]["home"]["id"]
        away_id = fixture["teams"]["away"]["id"]

        home_goals = fixture["goals"]["home"]
        away_goals = fixture["goals"]["away"]

        if home_goals is None or away_goals is None:
            continue

        if team_id == home_id:
            team_goals = home_goals
            opponent_goals = away_goals
        else:
            team_goals = away_goals
            opponent_goals = home_goals

        total += 1

        if team_goals > 0:
            scored += 1

        if opponent_goals > 0:
            conceded += 1

        if team_goals > 0 and opponent_goals > 0:
            btts += 1

    if total == 0:
        return None

    return {
        "total": total,
        "btts": btts,
        "btts_pct": btts / total * 100,
        "scored": scored,
        "scored_pct": scored / total * 100,
        "conceded": conceded,
        "conceded_pct": conceded / total * 100
    }


def level(value):
    if value >= 90:
        return "🔴 NIVEL 3"
    elif value >= 80:
        return "🟠 NIVEL 2"
    elif value >= 70:
        return "🟢 NIVEL 1"

    return None


def main():
    print("Iniciando monitor BTTS...")

    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not chat_id:
        chat_id = get_chat_id()

    if not chat_id:
        print("No se encontró un chat de Telegram.")
        print("Envía /start al bot y vuelve a ejecutar el programa.")
        return

    fixtures = get_today_fixtures()

    print(f"Partidos encontrados: {len(fixtures)}")

    alerts = 0

    for fixture in fixtures:

        status = fixture["fixture"]["status"]["short"]

        # Solo analizar partidos que todavía no hayan terminado
        if status in ["FT", "AET", "PEN", "CANC", "PST", "ABD"]:
            continue

        home = fixture["teams"]["home"]
        away = fixture["teams"]["away"]

        home_last = get_team_last_19(home["id"])
        away_last = get_team_last_19(away["id"])

        home_stats = calculate_btts(home_last, home["id"])
        away_stats = calculate_btts(away_last, away["id"])

        if not home_stats or not away_stats:
            continue

        # Exigir 19 partidos válidos
        if home_stats["total"] < 19 or away_stats["total"] < 19:
            continue

        combined = (
            home_stats["btts_pct"] +
            away_stats["btts_pct"]
        ) / 2

        alert_level = level(combined)

        if not alert_level:
            continue

        fixture_time = fixture["fixture"]["date"]

        message = f"""
🚨 ALERTA ESTADÍSTICA BTTS

{alert_level}

⚽ {home["name"]} vs {away["name"]}

🏆 {fixture["league"]["name"]}

🕐 {fixture_time}

📊 ÚLTIMOS 19 PARTIDOS

🏠 {home["name"]}
BTTS: {home_stats["btts"]}/19 ({home_stats["btts_pct"]:.1f}%)
Marcó: {home_stats["scored"]}/19 ({home_stats["scored_pct"]:.1f}%)
Recibió gol: {home_stats["conceded"]}/19 ({home_stats["conceded_pct"]:.1f}%)

✈️ {away["name"]}
BTTS: {away_stats["btts"]}/19 ({away_stats["btts_pct"]:.1f}%)
Marcó: {away_stats["scored"]}/19 ({away_stats["scored_pct"]:.1f}%)
Recibió gol: {away_stats["conceded"]}/19 ({away_stats["conceded_pct"]:.1f}%)

📈 INDICADOR COMBINADO
{combined:.1f}%

⚠️ Indicador estadístico. No garantiza el resultado.
"""

        send_message(chat_id, message)

        alerts += 1

    print(f"Alertas enviadas: {alerts}")


if __name__ == "__main__":
    main()
