import os
import time
import requests
from datetime import datetime, timedelta, timezone

# ============================================================
# CONFIGURACIÓN
# ============================================================

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

MIN_PROBABILITY = 70
LAST_MATCHES = 10

# API-Football
API_FOOTBALL_URL = "https://v3.football.api-sports.io"

# Football-data
FOOTBALL_DATA_URL = "https://api.football-data.org/v4"

# ============================================================
# COMPROBAR VARIABLES
# ============================================================

print("====================================")
print("⚽ FOOTBALL ALERTS")
print("====================================")

if API_FOOTBALL_KEY:
    print("🔑 API-Football: CONFIGURADA")
else:
    print("⚠️ API-Football: NO CONFIGURADA")

if FOOTBALL_DATA_API_KEY:
    print("🔑 Football-data: CONFIGURADA")
else:
    print("⚠️ Football-data: NO CONFIGURADA")

if TELEGRAM_TOKEN:
    print("🤖 Telegram: CONFIGURADO")
else:
    print("❌ Telegram: NO CONFIGURADO")

if CHAT_ID:
    print("💬 Chat ID: CONFIGURADO")
else:
    print("⚠️ Chat ID: NO CONFIGURADO")

print("====================================")

if not API_FOOTBALL_KEY and not FOOTBALL_DATA_API_KEY:
    print("")
    print("❌ NO HAY NINGUNA API CONFIGURADA")
    print("Revisa GitHub Secrets.")
    raise SystemExit(1)

if not TELEGRAM_TOKEN:
    print("")
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADO")
    raise SystemExit(1)


# ============================================================
# SESIONES
# ============================================================

session_af = requests.Session()

session_af.headers.update({
    "x-apisports-key": API_FOOTBALL_KEY or ""
})

session_fd = requests.Session()

session_fd.headers.update({
    "X-Auth-Token": FOOTBALL_DATA_API_KEY or "",
    "User-Agent": "FootballAlertsBot/2.0"
})


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensaje):

    if not CHAT_ID:
        print("")
        print("⚠️ TELEGRAM_CHAT_ID NO CONFIGURADO")
        print("Mensaje:")
        print(mensaje)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    try:

        response = requests.post(
            url,
            data=data,
            timeout=20
        )

        if response.status_code == 200:
            print("📨 Telegram: mensaje enviado")
            return True

        print(
            f"❌ Telegram HTTP {response.status_code}"
        )
        print(response.text)

    except Exception as e:
        print(f"❌ Error Telegram: {e}")

    return False


# ============================================================
# API-FOOTBALL
# ============================================================

def api_football_get(endpoint, params=None):

    if not API_FOOTBALL_KEY:
        return None

    url = API_FOOTBALL_URL + endpoint

    try:

        response = session_af.get(
            url,
            params=params,
            timeout=30
        )

        print(
            f"API-Football: {endpoint} "
            f"HTTP {response.status_code}"
        )

        if response.status_code == 200:
            return response.json()

        print(
            f"⚠️ API-Football error: "
            f"{response.text}"
        )

    except Exception as e:

        print(
            f"❌ Error API-Football: {e}"
        )

    return None


# ============================================================
# FOOTBALL-DATA
# ============================================================

def football_data_get(endpoint, params=None):

    if not FOOTBALL_DATA_API_KEY:
        return None

    url = FOOTBALL_DATA_URL + endpoint

    try:

        response = session_fd.get(
            url,
            params=params,
            timeout=30
        )

        print(
            f"Football-data: {endpoint} "
            f"HTTP {response.status_code}"
        )

        if response.status_code == 200:
            return response.json()

        print(
            f"⚠️ Football-data error: "
            f"{response.text}"
        )

    except Exception as e:

        print(
            f"❌ Error Football-data: {e}"
        )

    return None


# ============================================================
# PARTIDOS API-FOOTBALL
# ============================================================

def obtener_partidos_api_football():

    if not API_FOOTBALL_KEY:
        return []

    hoy = datetime.now(
        timezone.utc
    ).date()

    manana = hoy + timedelta(days=1)

    partidos = []

    for fecha in [
        hoy.isoformat(),
        manana.isoformat()
    ]:

        data = api_football_get(
            "/fixtures",
            {
                "date": fecha
            }
        )

        if not data:
            continue

        response = data.get(
            "response",
            []
        )

        for item in response:

            fixture = item.get(
                "fixture",
                {}
            )

            teams = item.get(
                "teams",
                {}
            )

            home = teams.get(
                "home",
                {}
            )

            away = teams.get(
                "away",
                {}
            )

            partido = {
                "id": fixture.get("id"),
                "date": fixture.get("date"),
                "home_id": home.get("id"),
                "home": home.get(
                    "name",
                    "Local"
                ),
                "away_id": away.get("id"),
                "away": away.get(
                    "name",
                    "Visitante"
                ),
                "league": item.get(
                    "league",
                    {}
                ).get(
                    "name",
                    "Liga"
                )
            }

            partidos.append(partido)

    # eliminar duplicados

    unicos = {}

    for partido in partidos:

        if partido["id"]:
            unicos[
                partido["id"]
            ] = partido

    resultado = list(
        unicos.values()
    )

    print(
        f"📊 API-Football encontró: "
        f"{len(resultado)} partidos"
    )

    return resultado


# ============================================================
# ÚLTIMOS PARTIDOS API-FOOTBALL
# ============================================================

def ultimos_partidos_api_football(
    team_id,
    limite=10
):

    if not API_FOOTBALL_KEY:
        return []

    data = api_football_get(
        "/fixtures",
        {
            "team": team_id,
            "last": limite
        }
    )

    if not data:
        return []

    return data.get(
        "response",
        []
    )


# ============================================================
# ESTADÍSTICAS
# ============================================================

def calcular_estadisticas(
    partidos,
    team_id
):

    if not partidos:
        return {
            "btts": 0,
            "over25": 0,
            "ht_draw": 0,
            "total": 0
        }

    btts = 0
    over25 = 0
    ht_draw = 0
    total = 0

    for partido in partidos:

        goals = partido.get(
            "goals",
            {}
        )

        score = partido.get(
            "score",
            {}
        )

        home_goals = goals.get(
            "home"
        )

        away_goals = goals.get(
            "away"
        )

        ht_home = (
            score.get(
                "halftime",
                {}
            ).get("home")
        )

        ht_away = (
            score.get(
                "halftime",
                {}
            ).get("away")
        )

        if (
            home_goals is None
            or away_goals is None
        ):
            continue

        total += 1

        # BTTS

        if (
            home_goals > 0
            and away_goals > 0
        ):
            btts += 1

        # OVER 2.5

        if (
            home_goals +
            away_goals
        ) > 2:
            over25 += 1

        # EMPATE DESCANSO

        if (
            ht_home is not None
            and ht_away is not None
            and ht_home == ht_away
        ):
            ht_draw += 1

    if total == 0:
        return {
            "btts": 0,
            "over25": 0,
            "ht_draw": 0,
            "total": 0
        }

    return {
        "btts": btts / total * 100,
        "over25": over25 / total * 100,
        "ht_draw": ht_draw / total * 100,
        "total": total
    }


# ============================================================
# ANALIZAR PARTIDO
# ============================================================

def analizar_partido(partido):

    home_id = partido["home_id"]
    away_id = partido["away_id"]

    if not home_id or not away_id:
        return None

    print("")
    print(
        f"🔎 {partido['home']} "
        f"vs {partido['away']}"
    )

    print(
        f"🏆 {partido['league']}"
    )

    home_matches = (
        ultimos_partidos_api_football(
            home_id,
            LAST_MATCHES
        )
    )

    time.sleep(1)

    away_matches = (
        ultimos_partidos_api_football(
            away_id,
            LAST_MATCHES
        )
    )

    time.sleep(1)

    if (
        len(home_matches) < 5
        or len(away_matches) < 5
    ):

        print(
            "⚠️ Insuficientes datos"
        )

        return None

    home_stats = calcular_estadisticas(
        home_matches,
        home_id
    )

    away_stats = calcular_estadisticas(
        away_matches,
        away_id
    )

    return {
        "home": partido["home"],
        "away": partido["away"],
        "league": partido["league"],
        "date": partido["date"],
        "btts": (
            home_stats["btts"]
            + away_stats["btts"]
        ) / 2,
        "over25": (
            home_stats["over25"]
            + away_stats["over25"]
        ) / 2,
        "ht_draw": (
            home_stats["ht_draw"]
            + away_stats["ht_draw"]
        ) / 2
    }


# ============================================================
# CREAR ALERTA
# ============================================================

def crear_alerta(resultado):

    señales = []

    if resultado["btts"] >= MIN_PROBABILITY:

        señales.append(
            f"⚽ <b>AMBOS MARCAN</b> "
            f"{resultado['btts']:.1f}%"
        )

    if resultado["over25"] >= MIN_PROBABILITY:

        señales.append(
            f"🔥 <b>OVER 2.5</b> "
            f"{resultado['over25']:.1f}%"
        )

    if resultado["ht_draw"] >= MIN_PROBABILITY:

        señales.append(
            f"🤝 <b>EMPATE 1T</b> "
            f"{resultado['ht_draw']:.1f}%"
        )

    if not señales:
        return None

    fecha = resultado["date"]

    mensaje = (
        "🚨 <b>FOOTBALL ALERTS</b>\n\n"
        f"🏆 {resultado['league']}\n"
        f"⚽ <b>{resultado['home']}</b> "
        f"vs "
        f"<b>{resultado['away']}</b>\n\n"
        + "\n".join(señales)
        + "\n\n"
        "💰 Apuesta sugerida: $5.000\n"
        "📊 Análisis: últimos 10 partidos\n"
        "⏰ Señal previa al partido"
    )

    return mensaje


# ============================================================
# MAIN
# ============================================================

def main():

    inicio = time.time()

    print("")
    print("====================================")
    print("🚀 INICIANDO ANÁLISIS")
    print("====================================")

    partidos = (
        obtener_partidos_api_football()
    )

    if not partidos:

        print(
            "⚠️ No se encontraron partidos."
        )

        return

    # Para las primeras pruebas
    MAX_PARTIDOS = 15

    partidos = partidos[
        :MAX_PARTIDOS
    ]

    señales = 0

    for partido in partidos:

        resultado = analizar_partido(
            partido
        )

        if not resultado:
            continue

        alerta = crear_alerta(
            resultado
        )

        if alerta:

            print(
                "🚨 SEÑAL ENCONTRADA"
            )

            enviar_telegram(
                alerta
            )

            señales += 1

        else:

            print(
                "ℹ️ Sin señal >70%"
            )

        time.sleep(2)

    tiempo = (
        time.time() - inicio
    )

    print("")
    print("====================================")
    print(
        f"🚨 Señales: {señales}"
    )
    print(
        f"⏱️ Tiempo: {tiempo:.1f} segundos"
    )
    print("====================================")
    print("✅ FINALIZADO")


if __name__ == "__main__":
    main()