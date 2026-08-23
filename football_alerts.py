import os
import time
import requests
from datetime import datetime, timedelta, timezone

# ============================================================
# CONFIGURACIÓN DE APIS
# ============================================================

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ============================================================
# VALIDACIÓN
# ============================================================

print("====================================")
print("⚽ FOOTBALL ALERTS")
print("====================================")

if API_FOOTBALL_KEY:
    print("🔑 API-Football: CONFIGURADA")
else:
    print("❌ API-Football: NO CONFIGURADA")

if FOOTBALL_DATA_API_KEY:
    print("🔑 Football-Data: CONFIGURADA")
else:
    print("⚠️ Football-Data: NO CONFIGURADA")

if TELEGRAM_TOKEN:
    print("🤖 Telegram: CONFIGURADO")
else:
    print("❌ Telegram: NO CONFIGURADO")

print("====================================")

if not API_FOOTBALL_KEY:
    print("")
    print("❌ API_FOOTBALL_KEY NO CONFIGURADA")
    print("Verifica el Secret de GitHub y el workflow.")
    raise SystemExit(1)

if not TELEGRAM_TOKEN:
    print("")
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADO")
    raise SystemExit(1)


# ============================================================
# API-FOOTBALL
# ============================================================

API_FOOTBALL_URL = "https://v3.football.api-sports.io"

api_football_session = requests.Session()

api_football_session.headers.update({
    "x-apisports-key": API_FOOTBALL_KEY
})


def api_football_get(endpoint, params=None):

    url = API_FOOTBALL_URL + endpoint

    try:

        response = api_football_session.get(
            url,
            params=params,
            timeout=30
        )

        print(
            f"API-Football: "
            f"{endpoint} HTTP {response.status_code}"
        )

        if response.status_code == 200:
            return response.json()

        print(
            f"❌ API-Football error: "
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

FOOTBALL_DATA_URL = "https://api.football-data.org/v4"

football_data_session = requests.Session()

if FOOTBALL_DATA_API_KEY:

    football_data_session.headers.update({
        "X-Auth-Token": FOOTBALL_DATA_API_KEY,
        "User-Agent": "FootballAlertsBot/2.0"
    })


def football_data_get(endpoint, params=None):

    if not FOOTBALL_DATA_API_KEY:
        return None

    url = FOOTBALL_DATA_URL + endpoint

    try:

        response = football_data_session.get(
            url,
            params=params,
            timeout=30
        )

        print(
            f"Football-Data: "
            f"{endpoint} HTTP {response.status_code}"
        )

        if response.status_code == 200:
            return response.json()

        print(
            f"⚠️ Football-Data error: "
            f"{response.text}"
        )

    except Exception as e:

        print(
            f"⚠️ Error Football-Data: {e}"
        )

    return None


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

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

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
            f"❌ Telegram HTTP "
            f"{response.status_code}: "
            f"{response.text}"
        )

    except Exception as e:

        print(
            f"❌ Error Telegram: {e}"
        )

    return False


# ============================================================
# PRUEBA DE API-FOOTBALL
# ============================================================

def probar_api_football():

    print("")
    print("====================================")
    print("🧪 PROBANDO API-FOOTBALL")
    print("====================================")

    data = api_football_get(
        "/status"
    )

    if data:

        print("✅ API-Football respondió correctamente")

        errors = data.get("errors")

        if errors:
            print(
                f"⚠️ Errores API: {errors}"
            )

        response = data.get(
            "response"
        )

        if response:
            print(
                "📡 Estado de API-Football OK"
            )

        return True

    print("❌ API-Football no respondió correctamente")

    return False


# ============================================================
# OBTENER PARTIDOS DE API-FOOTBALL
# ============================================================

def obtener_partidos_api_football():

    hoy = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    manana = (
        datetime.now(
            timezone.utc
        ) + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    print("")
    print("====================================")
    print("📅 PARTIDOS")
    print("====================================")

    partidos = []

    for fecha in [hoy, manana]:

        print(
            f"📅 Consultando {fecha}"
        )

        data = api_football_get(
            "/fixtures",
            {
                "date": fecha
            }
        )

        if not data:
            continue

        errores = data.get(
            "errors"
        )

        if errores:
            print(
                f"⚠️ API errors: {errores}"
            )
            continue

        resultados = data.get(
            "response",
            []
        )

        print(
            f"📊 Partidos encontrados "
            f"({fecha}): {len(resultados)}"
        )

        partidos.extend(
            resultados
        )

    # eliminar duplicados

    unicos = {}

    for partido in partidos:

        fixture = partido.get(
            "fixture",
            {}
        )

        partido_id = fixture.get(
            "id"
        )

        if partido_id:
            unicos[
                partido_id
            ] = partido

    partidos = list(
        unicos.values()
    )

    print(
        f"📊 TOTAL PARTIDOS: "
        f"{len(partidos)}"
    )

    return partidos


# ============================================================
# MOSTRAR PARTIDOS
# ============================================================

def mostrar_partidos(partidos):

    print("")
    print("====================================")
    print("⚽ PARTIDOS DISPONIBLES")
    print("====================================")

    for partido in partidos[:20]:

        fixture = partido.get(
            "fixture",
            {}
        )

        teams = partido.get(
            "teams",
            {}
        )

        league = partido.get(
            "league",
            {}
        )

        home = teams.get(
            "home",
            {}
        ).get(
            "name",
            "?"
        )

        away = teams.get(
            "away",
            {}
        ).get(
            "name",
            "?"
        )

        liga = league.get(
            "name",
            "?"
        )

        print(
            f"⚽ {home} vs {away} "
            f"| {liga}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    inicio = time.time()

    print("")
    print("====================================")
    print("🚀 INICIANDO ANÁLISIS")
    print("====================================")

    # Primero comprobamos API-Football

    if not probar_api_football():

        print(
            "❌ No se puede continuar."
        )

        return

    # Obtener partidos

    partidos = (
        obtener_partidos_api_football()
    )

    if not partidos:

        print("")
        print(
            "⚠️ No se encontraron partidos."
        )

        return

    mostrar_partidos(
        partidos
    )

    tiempo = (
        time.time() - inicio
    )

    print("")
    print("====================================")
    print(
        f"⏱️ Tiempo: {tiempo:.1f} segundos"
    )
    print("====================================")
    print("✅ Ejecución terminada")


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    main()