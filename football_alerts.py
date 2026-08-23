import os
import time
import json
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Apuesta fija
STAKE = 5000

# Probabilidad mínima
MIN_PROBABILITY = 70

# Últimos partidos
LAST_MATCHES = 10

# Máximo de partidos a analizar por ejecución
MAX_PARTIDOS_ANALIZAR = 30

# Archivos de datos
DATA_FILE = Path("apuestas.json")

# APIs
API_FOOTBALL_URL = "https://v3.football.api-sports.io"
FOOTBALL_DATA_URL = "https://api.football-data.org/v4"

# ============================================================
# VALIDACIÓN
# ============================================================

if not API_FOOTBALL_KEY:
    print("❌ API_FOOTBALL_KEY NO CONFIGURADA")
    raise SystemExit(1)

if not FOOTBALL_DATA_API_KEY:
    print("❌ FOOTBALL_DATA_API_KEY NO CONFIGURADA")
    raise SystemExit(1)

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADA")
    raise SystemExit(1)

print("====================================")
print("⚽ FOOTBALL ALERTS")
print("====================================")
print("🔑 API-Football: CONFIGURADA")
print("🔑 Football-Data: CONFIGURADA")
print("🤖 Telegram: CONFIGURADO")
print(f"💰 Apuesta: ${STAKE:,} COP")
print("====================================")


# ============================================================
# SESIONES
# ============================================================

api_session = requests.Session()

api_session.headers.update({
    "x-apisports-key": API_FOOTBALL_KEY,
    "User-Agent": "FootballAlertsBot/2.0"
})


football_session = requests.Session()

football_session.headers.update({
    "X-Auth-Token": FOOTBALL_DATA_API_KEY,
    "User-Agent": "FootballAlertsBot/2.0"
})


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensaje):

    if not CHAT_ID:
        print("⚠️ TELEGRAM_CHAT_ID no configurado.")
        print(mensaje)
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    try:

        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": mensaje,
                "parse_mode": "HTML"
            },
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

    url = API_FOOTBALL_URL + endpoint

    try:

        response = api_session.get(
            url,
            params=params,
            timeout=30
        )

        print(
            f"API-Football {endpoint} "
            f"HTTP {response.status_code}"
        )

        if response.status_code == 200:
            return response.json()

        print(response.text)

    except Exception as e:
        print(f"❌ Error API-Football: {e}")

    return None


# ============================================================
# FOOTBALL-DATA
# ============================================================

def football_data_get(endpoint, params=None):

    url = FOOTBALL_DATA_URL + endpoint

    try:

        response = football_session.get(
            url,
            params=params,
            timeout=30
        )

        print(
            f"Football-Data {endpoint} "
            f"HTTP {response.status_code}"
        )

        if response.status_code == 200:
            return response.json()

        print(response.text)

    except Exception as e:
        print(f"❌ Error Football-Data: {e}")

    return None


# ============================================================
# PARTIDOS DE API-FOOTBALL
# ============================================================

def obtener_partidos_api():

    hoy = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%d")

    manana = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    partidos = []

    for fecha in [hoy, manana]:

        data = api_football_get(
            "/fixtures",
            {
                "date": fecha,
                "status": "NS"
            }
        )

        if not data:
            continue

        for item in data.get("response", []):

            fixture = item.get(
                "fixture",
                {}
            )

            teams = item.get(
                "teams",
                {}
            )

            partidos.append({
                "id": fixture.get("id"),
                "date": fixture.get("date"),
                "home": teams.get(
                    "home",
                    {}
                ),
                "away": teams.get(
                    "away",
                    {}
                ),
                "league": item.get(
                    "league",
                    {}
                )
            })

    return partidos


# ============================================================
# HISTORIAL DE EQUIPO
# ============================================================

def obtener_historial_api(team_id):

    data = api_football_get(
        "/fixtures",
        {
            "team": team_id,
            "last": LAST_MATCHES
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

def calcular_estadisticas(partidos, team_id):

    if not partidos:
        return {}

    total = len(partidos)

    btts = 0
    over15 = 0
    over25 = 0
    over35 = 0
    under35 = 0
    empate_ht = 0
    victoria = 0
    empate = 0
    derrota = 0

    goles_favor = 0
    goles_contra = 0

    for partido in partidos:

        teams = partido.get(
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

        goals = partido.get(
            "goals",
            {}
        )

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        if home_goals is None or away_goals is None:
            continue

        total_goals = (
            home_goals +
            away_goals
        )

        if (
            home_goals > 0
            and away_goals > 0
        ):
            btts += 1

        if total_goals > 1:
            over15 += 1

        if total_goals > 2:
            over25 += 1

        if total_goals > 3:
            over35 += 1

        if total_goals < 4:
            under35 += 1

        halftime = partido.get(
            "score",
            {}
        ).get(
            "halftime",
            {}
        )

        ht_home = halftime.get("home")
        ht_away = halftime.get("away")

        if (
            ht_home is not None
            and ht_away is not None
            and ht_home == ht_away
        ):
            empate_ht += 1

        if home.get("id") == team_id:

            goles_favor += home_goals
            goles_contra += away_goals

            if home_goals > away_goals:
                victoria += 1
            elif home_goals == away_goals:
                empate += 1
            else:
                derrota += 1

        else:

            goles_favor += away_goals
            goles_contra += home_goals

            if away_goals > home_goals:
                victoria += 1
            elif away_goals == home_goals:
                empate += 1
            else:
                derrota += 1

    def porcentaje(valor):

        if total == 0:
            return 0

        return (
            valor / total
        ) * 100

    return {

        "btts": porcentaje(btts),

        "over15": porcentaje(over15),

        "over25": porcentaje(over25),

        "over35": porcentaje(over35),

        "under35": porcentaje(under35),

        "empate_ht": porcentaje(empate_ht),

        "victoria": porcentaje(victoria),

        "empate": porcentaje(empate),

        "derrota": porcentaje(derrota),

        "promedio_gf": (
            goles_favor / total
            if total else 0
        ),

        "promedio_gc": (
            goles_contra / total
            if total else 0
        ),

        "partidos": total
    }


# ============================================================
# ANALIZAR PARTIDO
# ============================================================

def analizar_partido(partido):

    home = partido["home"]
    away = partido["away"]

    home_id = home.get("id")
    away_id = away.get("id")

    home_name = home.get(
        "name",
        "Local"
    )

    away_name = away.get(
        "name",
        "Visitante"
    )

    print("")
    print(
        f"🔎 {home_name} vs {away_name}"
    )

    home_history = obtener_historial_api(
        home_id
    )

    time.sleep(0.5)

    away_history = obtener_historial_api(
        away_id
    )

    if (
        len(home_history) < 5
        or len(away_history) < 5
    ):

        print(
            "⚠️ Historial insuficiente"
        )

        return None

    home_stats = calcular_estadisticas(
        home_history,
        home_id
    )

    away_stats = calcular_estadisticas(
        away_history,
        away_id
    )

    resultado = {

        "fixture_id": partido["id"],

        "home": home_name,

        "away": away_name,

        "fecha": partido["date"],

        "liga": partido["league"].get(
            "name",
            "Desconocida"
        ),

        "btts": (
            home_stats["btts"]
            + away_stats["btts"]
        ) / 2,

        "over15": (
            home_stats["over15"]
            + away_stats["over15"]
        ) / 2,

        "over25": (
            home_stats["over25"]
            + away_stats["over25"]
        ) / 2,

        "over35": (
            home_stats["over35"]
            + away_stats["over35"]
        ) / 2,

        "under35": (
            home_stats["under35"]
            + away_stats["under35"]
        ) / 2,

        "empate_ht": (
            home_stats["empate_ht"]
            + away_stats["empate_ht"]
        ) / 2,

        "victoria_local": home_stats["victoria"],

        "victoria_visitante": away_stats["victoria"]
    }

    return resultado


# ============================================================
# CREAR SEÑALES
# ============================================================

def crear_señales(resultado):

    señales = []

    if resultado["btts"] >= MIN_PROBABILITY:

        señales.append({
            "mercado": "BTTS",
            "probabilidad": resultado["btts"]
        })

    if resultado["over15"] >= MIN_PROBABILITY:

        señales.append({
            "mercado": "OVER 1.5",
            "probabilidad": resultado["over15"]
        })

    if resultado["over25"] >= MIN_PROBABILITY:

        señales.append({
            "mercado": "OVER 2.5",
            "probabilidad": resultado["over25"]
        })

    if resultado["over35"] >= MIN_PROBABILITY:

        señales.append({
            "mercado": "OVER 3.5",
            "probabilidad": resultado["over35"]
        })

    if resultado["under35"] >= MIN_PROBABILITY:

        señales.append({
            "mercado": "UNDER 3.5",
            "probabilidad": resultado["under35"]
        })

    if resultado["empate_ht"] >= MIN_PROBABILITY:

        señales.append({
            "mercado": "EMPATE 1T",
            "probabilidad": resultado["empate_ht"]
        })

    return señales


# ============================================================
# GUARDAR APUESTAS
# ============================================================

def cargar_apuestas():

    if not DATA_FILE.exists():
        return []

    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as archivo:

            return json.load(archivo)

    except Exception:
        return []


def guardar_apuestas(apuestas):

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            apuestas,
            archivo,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# REGISTRAR SEÑAL
# ============================================================

def registrar_apuesta(
    resultado,
    señal
):

    apuestas = cargar_apuestas()

    apuesta = {

        "fixture_id":
            resultado["fixture_id"],

        "home":
            resultado["home"],

        "away":
            resultado["away"],

        "liga":
            resultado["liga"],

        "fecha":
            resultado["fecha"],

        "mercado":
            señal["mercado"],

        "probabilidad":
            round(
                señal["probabilidad"],
                2
            ),

        "stake":
            STAKE,

        "estado":
            "PENDIENTE",

        "ganancia":
            0,

        "creada":
            datetime.now(
                timezone.utc
            ).isoformat()
    }

    # Evitar duplicados
    for existente in apuestas:

        if (
            existente["fixture_id"]
            == apuesta["fixture_id"]
            and
            existente["mercado"]
            == apuesta["mercado"]
        ):
            return

    apuestas.append(apuesta)

    guardar_apuestas(apuestas)


# ============================================================
# CREAR MENSAJE
# ============================================================

def crear_mensaje(
    resultado,
    señales
):

    mensaje = (
        "🚨 <b>NUEVA SEÑAL</b>\n\n"
        f"⚽ <b>{resultado['home']}</b> "
        f"vs "
        f"<b>{resultado['away']}</b>\n\n"
        f"🏆 {resultado['liga']}\n\n"
    )

    for señal in señales:

        mensaje += (
            f"🎯 <b>{señal['mercado']}</b>\n"
            f"📊 Probabilidad: "
            f"<b>{señal['probabilidad']:.1f}%</b>\n"
            f"💰 Apuesta: "
            f"<b>${STAKE:,} COP</b>\n\n"
        )

    mensaje += (
        "📈 Análisis: últimos "
        f"{LAST_MATCHES} partidos\n"
        "⏳ Estado: PENDIENTE\n\n"
        "⚠️ Resultado se comprobará "
        "cuando termine el partido."
    )

    return mensaje


# ============================================================
# ESTADÍSTICAS
# ============================================================

def mostrar_estadisticas():

    apuestas = cargar_apuestas()

    ganadas = [
        a for a in apuestas
        if a["estado"] == "GANADA"
    ]

    perdidas = [
        a for a in apuestas
        if a["estado"] == "PERDIDA"
    ]

    pendientes = [
        a for a in apuestas
        if a["estado"] == "PENDIENTE"
    ]

    ganancia_total = sum(
        a.get("ganancia", 0)
        for a in apuestas
    )

    print("")
    print("====================================")
    print("📊 ESTADÍSTICAS")
    print("====================================")
    print(
        f"✅ Ganadas: {len(ganadas)}"
    )
    print(
        f"❌ Perdidas: {len(perdidas)}"
    )
    print(
        f"⏳ Pendientes: {len(pendientes)}"
    )
    print(
        f"💰 Balance: ${ganancia_total:,} COP"
    )
    print("====================================")


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

def main():

    inicio = time.time()

    print("")
    print("====================================")
    print("🚀 INICIANDO ANÁLISIS")
    print("====================================")

    partidos = obtener_partidos_api()

    print(
        f"📊 Partidos encontrados: "
        f"{len(partidos)}"
    )

    if not partidos:

        print(
            "⚠️ No se encontraron partidos."
        )

        return

    partidos = partidos[
        :MAX_PARTIDOS_ANALIZAR
    ]

    señales_enviadas = 0

    for partido in partidos:

        try:

            resultado = analizar_partido(
                partido
            )

            if not resultado:
                continue

            señales = crear_señales(
                resultado
            )

            if not señales:

                print(
                    "ℹ️ Sin señales >70%"
                )

                continue

            print(
                f"🚨 {len(señales)} "
                f"señales encontradas"
            )

            for señal in señales:

                registrar_apuesta(
                    resultado,
                    señal
                )

            mensaje = crear_mensaje(
                resultado,
                señales
            )

            if enviar_telegram(
                mensaje
            ):
                señales_enviadas += 1

            time.sleep(1)

        except Exception as e:

            print(
                f"❌ Error analizando partido: "
                f"{e}"
            )

    mostrar_estadisticas()

    tiempo = (
        time.time() - inicio
    )

    print("")
    print("====================================")
    print(
        f"📨 Señales enviadas: "
        f"{señales_enviadas}"
    )
    print(
        f"⏱️ Tiempo: "
        f"{tiempo:.1f} segundos"
    )
    print("====================================")
    print("✅ EJECUCIÓN TERMINADA")
    print("====================================")


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    main()