import os
import requests
from datetime import datetime, timedelta, timezone

API_KEY = os.environ["API_FOOTBALL_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

API_URL = "https://v3.football.api-sports.io"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

HEADERS = {
    "x-apisports-key": API_KEY
}

session = requests.Session()
session.headers.update(HEADERS)

# Evita pedir los mismos datos varias veces
team_cache = {}


def api_get(endpoint, params):
    response = session.get(
        f"{API_URL}/{endpoint}",
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if data.get("errors"):
        print("Error API:", data["errors"])

    return data.get("response", [])


def telegram_send(text):
    if not CHAT_ID:
        print("TELEGRAM_CHAT_ID no configurado.")
        return

    response = requests.post(
        f"{TELEGRAM_URL}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text
        },
        timeout=30
    )

    if not response.ok:
        print("Error Telegram:", response.text)


def get_fixtures_tomorrow():

    tomorrow = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    print(f"Buscando partidos del: {tomorrow}")

    return api_get(
        "fixtures",
        {
            "date": tomorrow
        }
    )


def get_last_10(team_id):

    if team_id in team_cache:
        return team_cache[team_id]

    fixtures = api_get(
        "fixtures",
        {
            "team": team_id,
            "last": 10
        }
    )

    team_cache[team_id] = fixtures

    return fixtures


def get_team_stats(team_id):

    fixtures = get_last_10(team_id)

    total = 0

    btts = 0
    over25 = 0
    halftime_draw = 0

    scored = 0
    conceded = 0

    for fixture in fixtures:

        goals = fixture.get("goals", {})
        score = fixture.get("score", {})

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        halftime = score.get("halftime", {})

        ht_home = halftime.get("home")
        ht_away = halftime.get("away")

        if (
            home_goals is None
            or away_goals is None
            or ht_home is None
            or ht_away is None
        ):
            continue

        home_id = fixture["teams"]["home"]["id"]

        if team_id == home_id:
            team_goals = home_goals
            opponent_goals = away_goals
        else:
            team_goals = away_goals
            opponent_goals = home_goals

        total += 1

        # Ambos marcan
        if team_goals > 0 and opponent_goals > 0:
            btts += 1

        # Más de 2.5
        if home_goals + away_goals > 2:
            over25 += 1

        # Empate al descanso
        if ht_home == ht_away:
            halftime_draw += 1

        if team_goals > 0:
            scored += 1

        if opponent_goals > 0:
            conceded += 1

    if total == 0:
        return None

    return {
        "total": total,
        "btts": btts,
        "btts_pct": btts / total * 100,
        "over25": over25,
        "over25_pct": over25 / total * 100,
        "ht_draw": halftime_draw,
        "ht_draw_pct": halftime_draw / total * 100,
        "scored_pct": scored / total * 100,
        "conceded_pct": conceded / total * 100
    }


def combined_percentage(a, b):

    return (a + b) / 2


def main():

    print("========================================")
    print("       BOT DE ALERTAS FUTBOL")
    print("========================================")

    fixtures = get_fixtures_tomorrow()

    print(
        f"Partidos encontrados: {len(fixtures)}"
    )

    alerts = 0

    for fixture in fixtures:

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

        print(
            f"\nAnalizando: "
            f"{home['name']} vs {away['name']}"
        )

        home_stats = get_team_stats(
            home["id"]
        )

        away_stats = get_team_stats(
            away["id"]
        )

        if not home_stats or not away_stats:
            print("Sin suficientes estadísticas.")
            continue

        if (
            home_stats["total"] < 10
            or away_stats["total"] < 10
        ):
            print("No hay 10 partidos válidos.")
            continue

        alerts_found = []

        # ==============================
        # BTTS
        # ==============================

        btts_probability = combined_percentage(
            home_stats["btts_pct"],
            away_stats["btts_pct"]
        )

        if btts_probability > 70:

            alerts_found.append(
                f"⚽ AMBOS MARCAN: "
                f"{btts_probability:.1f}%"
            )

        # ==============================
        # OVER 2.5
        # ==============================

        over25_probability = combined_percentage(
            home_stats["over25_pct"],
            away_stats["over25_pct"]
        )

        if over25_probability > 70:

            alerts_found.append(
                f"🔥 MÁS DE 2.5 GOLES: "
                f"{over25_probability:.1f}%"
            )

        # ==============================
        # EMPATE PRIMER TIEMPO
        # ==============================

        halftime_probability = combined_percentage(
            home_stats["ht_draw_pct"],
            away_stats["ht_draw_pct"]
        )

        if halftime_probability > 70:

            alerts_found.append(
                f"🤝 EMPATE 1ER TIEMPO: "
                f"{halftime_probability:.1f}%"
            )

        # ==============================
        # SI NO CUMPLE NINGUNA REGLA
        # ==============================

        if not alerts_found:

            print("Sin alerta.")

            continue

        alerts += 1

        match_date = fixture["fixture"]["date"]

        message = f"""
🚨 ALERTA ESTADÍSTICA 🚨

⚽ {home['name']} vs {away['name']}

🏆 {fixture['league']['name']}

🗓️ {match_date}

📊 ÚLTIMOS 10 PARTIDOS

🏠 {home['name']}

⚽ BTTS:
{home_stats['btts_pct']:.1f}%

🔥 Over 2.5:
{home_stats['over25_pct']:.1f}%

🤝 Empate 1er tiempo:
{home_stats['ht_draw_pct']:.1f}%


✈️ {away['name']}

⚽ BTTS:
{away_stats['btts_pct']:.1f}%

🔥 Over 2.5:
{away_stats['over25_pct']:.1f}%

🤝 Empate 1er tiempo:
{away_stats['ht_draw_pct']:.1f}%


🎯 PATRONES DETECTADOS

"""

        for alert in alerts_found:

            message += f"✅ {alert}\n"

        message += """

📌 Indicadores basados en los últimos
10 partidos disponibles.

⚠️ Estadística histórica, no garantía
de resultado.
"""

        print(message)

        telegram_send(message)

    print("\n========================================")
    print(f"ALERTAS ENVIADAS: {alerts}")
    print("========================================")


if __name__ == "__main__":
    main()
