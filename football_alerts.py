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
        print("Error obteniendo mensajes de Telegram")
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


def calculate_stats(fixtures, team_id):

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
        "scored_pct": scored / total * 100,
        "conceded_pct": conceded / total * 100
    }


def main():

    print("====================================")
    print("     MONITOR BTTS - PRUEBA")
    print("====================================")

    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not chat_id:
        chat_id = get_chat_id()

    if not chat_id:

        print("")
        print("No se encontró CHAT ID de Telegram.")
        print("Envía /start al bot y vuelve a ejecutar.")
        print("")

    fixtures = get_today_fixtures()

    print(f"Partidos encontrados: {len(fixtures)}")
    print("Analizando los primeros 20...")
    print("")

    alerts = 0

    for fixture in fixtures[:20]:

        status = fixture["fixture"]["status"]["short"]

        if status in [
            "FT",
            "AET",
            "PEN",
            "CANC",
            "PST",
            "ABD"
        ]:
            continue

        home = fixture["teams"]["home"]
        away = fixture["teams"]["away"]

        print("------------------------------------")
        print(f"{home['name']} vs {away['name']}")

        home_last = get_team_last_19(home["id"])
        away_last = get_team_last_19(away["id"])

        home_stats = calculate_stats(
            home_last,
            home["id"]
        )

        away_stats = calculate_stats(
            away_last,
            away["id"]
        )

        if not home_stats or not away_stats:

            print("Sin suficientes datos")
            continue

        print(
            f"{home['name']} - "
            f"BTTS últimos {home_stats['total']}: "
            f"{home_stats['btts_pct']:.1f}%"
        )

        print(
            f"{away['name']} - "
            f"BTTS últimos {away_stats['total']}: "
            f"{away_stats['btts_pct']:.1f}%"
        )

        if (
            home_stats["total"] < 19
            or away_stats["total"] < 19
        ):

            print("No tiene 19 partidos completos")
            continue

        combined = (
            home_stats["btts_pct"]
            + away_stats["btts_pct"]
        ) / 2

        print(
            f"INDICADOR COMBINADO: "
            f"{combined:.1f}%"
        )

        if combined >= 90:

            level = "🔴 NIVEL 3"

        elif combined >= 80:

            level = "🟠 NIVEL 2"

        elif combined >= 70:

            level = "🟢 NIVEL 1"

        else:

            print("NO ALERTA")
            continue

        print(f"ALERTA: {level}")

        message = f"""
🚨 ALERTA BTTS

{level}

⚽ {home['name']} vs {away['name']}

📊 Últimos 19 partidos

🏠 {home['name']}
BTTS: {home_stats['btts_pct']:.1f}%

✈️ {away['name']}
BTTS: {away_stats['btts_pct']:.1f}%

📈 Indicador combinado:
{combined:.1f}%

⚠️ Indicador estadístico.
No garantiza el resultado.
"""

        if chat_id:

            send_message(
                chat_id,
                message
            )

            alerts += 1

    print("")
    print("====================================")
    print(f"Alertas enviadas: {alerts}")
    print("====================================")


if __name__ == "__main__":
    main()
