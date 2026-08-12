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

# Guardamos resultados para no consultar dos veces al mismo equipo
team_cache = {}

# Para evitar mandar la misma alerta repetidamente
sent_alerts = set()


def api_get(endpoint, params):

    try:
        r = session.get(
            f"{API_URL}/{endpoint}",
            params=params,
            timeout=30
        )

        data = r.json()

        if not r.ok:
            print("Error HTTP:", r.status_code)
            print(data)
            return []

        if data.get("errors"):
            print("Error API:", data["errors"])
            return []

        return data.get("response", [])

    except Exception as e:
        print("Error de conexión:", e)
        return []


def send_telegram(message):

    if not CHAT_ID:
        print("TELEGRAM_CHAT_ID no está configurado.")
        return False

    try:

        r = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=30
        )

        if r.ok:
            return True

        print("Error Telegram:", r.text)
        return False

    except Exception as e:
        print("Error enviando Telegram:", e)
        return False


def get_tomorrow():

    return (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")


def get_tomorrow_fixtures():

    tomorrow = get_tomorrow()

    print("")
    print("Buscando partidos del:", tomorrow)

    fixtures = api_get(
        "fixtures",
        {
            "date": tomorrow
        }
    )

    return fixtures


def get_last_10(team_id, before_date):

    cache_key = (
        team_id,
        before_date
    )

    if cache_key in team_cache:
        return team_cache[cache_key]

    # Buscamos aproximadamente 3 meses hacia atrás.
    # No utilizamos last=10 porque el plan gratuito no lo permite.

    before = datetime.strptime(
        before_date,
        "%Y-%m-%d"
    )

    start = before - timedelta(days=120)

    fixtures = api_get(
        "fixtures",
        {
            "team": team_id,
            "from": start.strftime("%Y-%m-%d"),
            "to": (
                before - timedelta(days=1)
            ).strftime("%Y-%m-%d")
        }
    )

    finished = []

    for f in fixtures:

        status = f["fixture"]["status"]["short"]

        if status in [
            "FT",
            "AET",
            "PEN"
        ]:

            finished.append(f)

    # Ordenar del más reciente al más antiguo

    finished.sort(
        key=lambda x: x["fixture"]["date"],
        reverse=True
    )

    result = finished[:10]

    team_cache[cache_key] = result

    return result


def calculate_stats(fixtures, team_id):

    total = 0

    btts = 0
    over25 = 0
    halftime_draw = 0

    for f in fixtures:

        goals = f.get("goals", {})
        score = f.get("score", {})

        hg = goals.get("home")
        ag = goals.get("away")

        ht = score.get("halftime", {})

        hth = ht.get("home")
        hta = ht.get("away")

        if (
            hg is None
            or ag is None
            or hth is None
            or hta is None
        ):
            continue

        total += 1

        # Ambos marcan

        if hg > 0 and ag > 0:
            btts += 1

        # Más de 2.5 goles

        if hg + ag >= 3:
            over25 += 1

        # Empate al descanso

        if hth == hta:
            halftime_draw += 1

    if total == 0:
        return None

    return {
        "total": total,
        "btts_pct": btts / total * 100,
        "over25_pct": over25 / total * 100,
        "ht_draw_pct": halftime_draw / total * 100
    }


def average(a, b):

    return (a + b) / 2


def main():

    print("")
    print("======================================")
    print("       BOT BTTS / OVER / HT")
    print("======================================")

    fixtures = get_tomorrow_fixtures()

    print(
        "Partidos encontrados:",
        len(fixtures)
    )

    if not fixtures:
        print("No se encontraron partidos.")
        return

    alerts = 0

    tomorrow = get_tomorrow()

    for index, fixture in enumerate(fixtures, 1):

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

        print("")
        print(
            f"[{index}/{len(fixtures)}] "
            f"{home['name']} vs {away['name']}"
        )

        home_history = get_last_10(
            home["id"],
            tomorrow
        )

        away_history = get_last_10(
            away["id"],
            tomorrow
        )

        if (
            len(home_history) < 10
            or len(away_history) < 10
        ):

            print(
                "Menos de 10 partidos disponibles."
            )

            continue

        home_stats = calculate_stats(
            home_history,
            home["id"]
        )

        away_stats = calculate_stats(
            away_history,
            away["id"]
        )

        if not home_stats or not away_stats:
            continue

        # ==============================
        # BTTS
        # ==============================

        btts = average(
            home_stats["btts_pct"],
            away_stats["btts_pct"]
        )

        # ==============================
        # OVER 2.5
        # ==============================

        over25 = average(
            home_stats["over25_pct"],
            away_stats["over25_pct"]
        )

        # ==============================
        # EMPATE AL DESCANSO
        # ==============================

        ht_draw = average(
            home_stats["ht_draw_pct"],
            away_stats["ht_draw_pct"]
        )

        print(
            f"BTTS: {btts:.1f}% | "
            f"Over 2.5: {over25:.1f}% | "
            f"HT Draw: {ht_draw:.1f}%"
        )

        detected = []

        if btts > 70:

            detected.append(
                f"⚽ Ambos marcan: {btts:.1f}%"
            )

        if over25 > 70:

            detected.append(
                f"🔥 Más de 2.5 goles: {over25:.1f}%"
            )

        if ht_draw > 70:

            detected.append(
                f"🤝 Empate 1er tiempo: {ht_draw:.1f}%"
            )

        if not detected:
            continue

        # Identificador para evitar duplicados

        alert_id = (
            f"{tomorrow}_"
            f"{home['id']}_"
            f"{away['id']}"
        )

        if alert_id in sent_alerts:
            continue

        sent_alerts.add(alert_id)

        message = f"""
🚨 ALERTA ESTADÍSTICA 🚨

⚽ {home['name']} vs {away['name']}

🏆 {fixture['league']['name']}

📅 {tomorrow}

━━━━━━━━━━━━━━━━
📊 ÚLTIMOS 10 PARTIDOS
━━━━━━━━━━━━━━━━

🏠 {home['name']}

⚽ BTTS:
{home_stats['btts_pct']:.1f}%

🔥 Over 2.5:
{home_stats['over25_pct']:.1f}%

🤝 Empate 1T:
{home_stats['ht_draw_pct']:.1f}%


✈️ {away['name']}

⚽ BTTS:
{away_stats['btts_pct']:.1f}%

🔥 Over 2.5:
{away_stats['over25_pct']:.1f}%

🤝 Empate 1T:
{away_stats['ht_draw_pct']:.1f}%

━━━━━━━━━━━━━━━━
🎯 PATRONES >70%
━━━━━━━━━━━━━━━━
"""

        for item in detected:
            message += f"\n✅ {item}"

        message += """

━━━━━━━━━━━━━━━━

📌 Indicador calculado usando
los últimos 10 partidos disponibles.

⚠️ Es una señal estadística y
no garantiza el resultado.
"""

        print("")
        print(message)

        if send_telegram(message):

            alerts += 1
            print("✅ Alerta enviada a Telegram.")

        else:

            print("❌ No se pudo enviar la alerta.")

    print("")
    print("======================================")
    print("ANÁLISIS TERMINADO")
    print("======================================")
    print(
        "Equipos consultados:",
        len(team_cache)
    )
    print(
        "Alertas enviadas:",
        alerts
    )
    print("======================================")


if __name__ == "__main__":
    main()
