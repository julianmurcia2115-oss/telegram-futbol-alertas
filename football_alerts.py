import os
import time
import requests
from datetime import datetime, timedelta, timezone

# ============================================================
# CONFIGURACIÓN
# ============================================================

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"

MIN_PROBABILITY = 70
LAST_MATCHES = 10

# Apuesta fija
STAKE = 5000

# Máximo de partidos a analizar por ejecución
MAX_PARTIDOS = 20


# ============================================================
# VALIDACIÓN
# ============================================================

print("====================================")
print("⚽ FOOTBALL ALERTS")
print("====================================")

if not API_FOOTBALL_KEY:
    print("❌ API_FOOTBALL_KEY NO CONFIGURADA")
    raise SystemExit(1)

print("🔑 API-Football: CONFIGURADA")

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADO")
    raise SystemExit(1)

print("🤖 Telegram: CONFIGURADO")

if CHAT_ID:
    print("💬 Telegram Chat ID: CONFIGURADO")
else:
    print("⚠️ TELEGRAM_CHAT_ID NO CONFIGURADO")

print("====================================")


# ============================================================
# SESIÓN
# ============================================================

session = requests.Session()

session.headers.update({
    "x-apisports-key": API_FOOTBALL_KEY,
    "Accept": "application/json",
    "User-Agent": "FootballAlertsBot/2.0"
})


# ============================================================
# API FOOTBALL
# ============================================================

def api_get(endpoint, params=None):

    url = BASE_URL + endpoint

    try:

        response = session.get(
            url,
            params=params,
            timeout=30
        )

        print(
            f"API-Football: {endpoint} "
            f"HTTP {response.status_code}"
        )

        if response.status_code == 200:

            data = response.json()

            errores = data.get("errors")

            if errores:
                print(
                    f"⚠️ API-Football errors: "
                    f"{errores}"
                )

            return data

        if response.status_code == 429:

            print(
                "⚠️ Límite de API-Football alcanzado."
            )

            print(
                response.text
            )

            return None

        print(
            f"❌ API-Football HTTP "
            f"{response.status_code}: "
            f"{response.text}"
        )

    except requests.exceptions.RequestException as e:

        print(
            f"❌ Error conexión API-Football: {e}"
        )

    return None


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensaje):

    if not CHAT_ID:

        print(
            "⚠️ TELEGRAM_CHAT_ID no configurado."
        )

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

            print(
                "📨 Telegram: mensaje enviado"
            )

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
# PARTIDOS DE HOY Y MAÑANA
# ============================================================

def obtener_partidos():

    hoy = datetime.now(
        timezone.utc
    ).date()

    manana = hoy + timedelta(days=1)

    print("")
    print(
        f"📅 Buscando partidos "
        f"{hoy} y {manana}"
    )

    partidos = []

    # --------------------------------------------------------
    # HOY
    # --------------------------------------------------------

    data_hoy = api_get(
        "/fixtures",
        {
            "date": hoy.isoformat(),
            "timezone": "America/Bogota"
        }
    )

    if data_hoy:

        partidos.extend(
            data_hoy.get(
                "response",
                []
            )
        )

    # --------------------------------------------------------
    # MAÑANA
    # --------------------------------------------------------

    data_manana = api_get(
        "/fixtures",
        {
            "date": manana.isoformat(),
            "timezone": "America/Bogota"
        }
    )

    if data_manana:

        partidos.extend(
            data_manana.get(
                "response",
                []
            )
        )

    # --------------------------------------------------------
    # ELIMINAR DUPLICADOS
    # --------------------------------------------------------

    unicos = {}

    for partido in partidos:

        fixture = partido.get(
            "fixture",
            {}
        )

        fixture_id = fixture.get(
            "id"
        )

        if fixture_id:
            unicos[fixture_id] = partido

    resultado = list(
        unicos.values()
    )

    print(
        f"📊 Partidos encontrados: "
        f"{len(resultado)}"
    )

    return resultado


# ============================================================
# ÚLTIMOS 10 PARTIDOS
# ============================================================

def obtener_ultimos_partidos(team_id):

    print(
        f"📈 Últimos {LAST_MATCHES} "
        f"partidos del equipo {team_id}"
    )

    data = api_get(
        "/fixtures",
        {
            "team": team_id,
            "last": LAST_MATCHES
        }
    )

    if not data:
        return []

    partidos = data.get(
        "response",
        []
    )

    return partidos


# ============================================================
# EXTRAER GOLES
# ============================================================

def obtener_goles(partido):

    goals = partido.get(
        "goals",
        {}
    )

    home = goals.get(
        "home"
    )

    away = goals.get(
        "away"
    )

    if home is None or away is None:
        return None, None

    return home, away


# ============================================================
# BTTS
# ============================================================

def calcular_btts(partidos):

    if not partidos:
        return 0

    validos = 0
    btts = 0

    for partido in partidos:

        home, away = obtener_goles(
            partido
        )

        if home is None or away is None:
            continue

        validos += 1

        if home > 0 and away > 0:
            btts += 1

    if validos == 0:
        return 0

    return (
        btts / validos
    ) * 100


# ============================================================
# OVER 1.5
# ============================================================

def calcular_over15(partidos):

    if not partidos:
        return 0

    validos = 0
    total = 0

    for partido in partidos:

        home, away = obtener_goles(
            partido
        )

        if home is None or away is None:
            continue

        validos += 1

        if home + away > 1:
            total += 1

    if validos == 0:
        return 0

    return (
        total / validos
    ) * 100


# ============================================================
# OVER 2.5
# ============================================================

def calcular_over25(partidos):

    if not partidos:
        return 0

    validos = 0
    total = 0

    for partido in partidos:

        home, away = obtener_goles(
            partido
        )

        if home is None or away is None:
            continue

        validos += 1

        if home + away > 2:
            total += 1

    if validos == 0:
        return 0

    return (
        total / validos
    ) * 100


# ============================================================
# OVER 3.5
# ============================================================

def calcular_over35(partidos):

    if not partidos:
        return 0

    validos = 0
    total = 0

    for partido in partidos:

        home, away = obtener_goles(
            partido
        )

        if home is None or away is None:
            continue

        validos += 1

        if home + away > 3:
            total += 1

    if validos == 0:
        return 0

    return (
        total / validos
    ) * 100


# ============================================================
# UNDER 3.5
# ============================================================

def calcular_under35(partidos):

    if not partidos:
        return 0

    validos = 0
    total = 0

    for partido in partidos:

        home, away = obtener_goles(
            partido
        )

        if home is None or away is None:
            continue

        validos += 1

        if home + away < 4:
            total += 1

    if validos == 0:
        return 0

    return (
        total / validos
    ) * 100


# ============================================================
# GANADOR LOCAL
# ============================================================

def calcular_local_gana(partidos, team_id):

    if not partidos:
        return 0

    validos = 0
    ganados = 0

    for partido in partidos:

        home, away = obtener_goles(
            partido
        )

        if home is None or away is None:
            continue

        validos += 1

        teams = partido.get(
            "teams",
            {}
        )

        home_team = teams.get(
            "home",
            {}
        )

        away_team = teams.get(
            "away",
            {}
        )

        local = (
            home_team.get("id")
            == team_id
        )

        if local:

            if home > away:
                ganados += 1

        else:

            if away > home:
                ganados += 1

    if validos == 0:
        return 0

    return (
        ganados / validos
    ) * 100


# ============================================================
# EMPATE
# ============================================================

def calcular_empate(partidos):

    if not partidos:
        return 0

    validos = 0
    empates = 0

    for partido in partidos:

        home, away = obtener_goles(
            partido
        )

        if home is None or away is None:
            continue

        validos += 1

        if home == away:
            empates += 1

    if validos == 0:
        return 0

    return (
        empates / validos
    ) * 100


# ============================================================
# ANALIZAR PARTIDO
# ============================================================

def analizar_partido(partido):

    fixture = partido.get(
        "fixture",
        {}
    )

    teams = partido.get(
        "teams",
        {}
    )

    home_team = teams.get(
        "home",
        {}
    )

    away_team = teams.get(
        "away",
        {}
    )

    fixture_id = fixture.get(
        "id"
    )

    home_name = home_team.get(
        "name",
        "Local"
    )

    away_name = away_team.get(
        "name",
        "Visitante"
    )

    home_id = home_team.get(
        "id"
    )

    away_id = away_team.get(
        "id"
    )

    if not home_id or not away_id:
        return None

    print("")
    print(
        f"🔎 Analizando: "
        f"{home_name} vs {away_name}"
    )

    # --------------------------------------------------------
    # ÚLTIMOS 10 LOCAL
    # --------------------------------------------------------

    home_matches = obtener_ultimos_partidos(
        home_id
    )

    time.sleep(0.5)

    # --------------------------------------------------------
    # ÚLTIMOS 10 VISITANTE
    # --------------------------------------------------------

    away_matches = obtener_ultimos_partidos(
        away_id
    )

    if (
        len(home_matches) < 5
        or len(away_matches) < 5
    ):

        print(
            "⚠️ Insuficientes datos."
        )

        return None

    # --------------------------------------------------------
    # ESTADÍSTICAS
    # --------------------------------------------------------

    btts_home = calcular_btts(
        home_matches
    )

    btts_away = calcular_btts(
        away_matches
    )

    over15_home = calcular_over15(
        home_matches
    )

    over15_away = calcular_over15(
        away_matches
    )

    over25_home = calcular_over25(
        home_matches
    )

    over25_away = calcular_over25(
        away_matches
    )

    over35_home = calcular_over35(
        home_matches
    )

    over35_away = calcular_over35(
        away_matches
    )

    under35_home = calcular_under35(
        home_matches
    )

    under35_away = calcular_under35(
        away_matches
    )

    local_home = calcular_local_gana(
        home_matches,
        home_id
    )

    local_away = calcular_local_gana(
        away_matches,
        away_id
    )

    empate_home = calcular_empate(
        home_matches
    )

    empate_away = calcular_empate(
        away_matches
    )

    # --------------------------------------------------------
    # PROMEDIOS
    # --------------------------------------------------------

    btts = (
        btts_home +
        btts_away
    ) / 2

    over15 = (
        over15_home +
        over15_away
    ) / 2

    over25 = (
        over25_home +
        over25_away
    ) / 2

    over35 = (
        over35_home +
        over35_away
    ) / 2

    under35 = (
        under35_home +
        under35_away
    ) / 2

    empate = (
        empate_home +
        empate_away
    ) / 2

    # --------------------------------------------------------
    # PREDICCIÓN DE API-FOOTBALL
    # --------------------------------------------------------

    prediction = api_get(
        "/predictions",
        {
            "fixture": fixture_id
        }
    )

    pred_home = None
    pred_draw = None
    pred_away = None

    if prediction:

        response = prediction.get(
            "response",
            []
        )

        if response:

            predictions = response[0].get(
                "predictions",
                {}
            )

            percent = predictions.get(
                "percent",
                {}
            )

            pred_home = convertir_porcentaje(
                percent.get("home")
            )

            pred_draw = convertir_porcentaje(
                percent.get("draw")
            )

            pred_away = convertir_porcentaje(
                percent.get("away")
            )

    return {
        "fixture_id": fixture_id,
        "home": home_name,
        "away": away_name,
        "btts": btts,
        "over15": over15,
        "over25": over25,
        "over35": over35,
        "under35": under35,
        "empate": empate,
        "pred_home": pred_home,
        "pred_draw": pred_draw,
        "pred_away": pred_away
    }


# ============================================================
# CONVERTIR %
# ============================================================

def convertir_porcentaje(valor):

    if valor is None:
        return None

    try:

        return float(
            str(valor)
            .replace("%", "")
            .strip()
        )

    except Exception:

        return None


# ============================================================
# CREAR SEÑALES
# ============================================================

def crear_alerta(resultado):

    if not resultado:
        return None

    home = resultado["home"]
    away = resultado["away"]

    señales = []

    # --------------------------------------------------------
    # BTTS
    # --------------------------------------------------------

    if resultado["btts"] >= MIN_PROBABILITY:

        señales.append(
            (
                "⚽ BTTS",
                resultado["btts"]
            )
        )

    # --------------------------------------------------------
    # OVER 1.5
    # --------------------------------------------------------

    if resultado["over15"] >= MIN_PROBABILITY:

        señales.append(
            (
                "🔥 OVER 1.5",
                resultado["over15"]
            )
        )

    # --------------------------------------------------------
    # OVER 2.5
    # --------------------------------------------------------

    if resultado["over25"] >= MIN_PROBABILITY:

        señales.append(
            (
                "🔥 OVER 2.5",
                resultado["over25"]
            )
        )

    # --------------------------------------------------------
    # OVER 3.5
    # --------------------------------------------------------

    if resultado["over35"] >= MIN_PROBABILITY:

        señales.append(
            (
                "🔥 OVER 3.5",
                resultado["over35"]
            )
        )

    # --------------------------------------------------------
    # UNDER 3.5
    # --------------------------------------------------------

    if resultado["under35"] >= MIN_PROBABILITY:

        señales.append(
            (
                "🧊 UNDER 3.5",
                resultado["under35"]
            )
        )

    # --------------------------------------------------------
    # EMPATE
    # --------------------------------------------------------

    if resultado["empate"] >= MIN_PROBABILITY:

        señales.append(
            (
                "🤝 EMPATE",
                resultado["empate"]
            )
        )

    # --------------------------------------------------------
    # PREDICCIÓN LOCAL
    # --------------------------------------------------------

    if (
        resultado["pred_home"] is not None
        and resultado["pred_home"] >= MIN_PROBABILITY
    ):

        señales.append(
            (
                f"🏠 GANA {home}",
                resultado["pred_home"]
            )
        )

    # --------------------------------------------------------
    # PREDICCIÓN EMPATE
    # --------------------------------------------------------

    if (
        resultado["pred_draw"] is not None
        and resultado["pred_draw"] >= MIN_PROBABILITY
    ):

        señales.append(
            (
                "🤝 EMPATE",
                resultado["pred_draw"]
            )
        )

    # --------------------------------------------------------
    # PREDICCIÓN VISITANTE
    # --------------------------------------------------------

    if (
        resultado["pred_away"] is not None
        and resultado["pred_away"] >= MIN_PROBABILITY
    ):

        señales.append(
            (
                f"✈️ GANA {away}",
                resultado["pred_away"]
            )
        )

    # --------------------------------------------------------
    # NO HAY SEÑAL
    # --------------------------------------------------------

    if not señales:
        return None

    # --------------------------------------------------------
    # CREAR TEXTO
    # --------------------------------------------------------

    ahora = datetime.now(
        timezone.utc
    )

    fecha = ahora.strftime(
        "%d/%m/%Y %H:%M"
    )

    texto = []

    texto.append(
        "🚨 <b>SEÑAL FOOTBALL ALERTS</b>"
    )

    texto.append("")

    texto.append(
        f"⚽ <b>{home}</b> vs "
        f"<b>{away}</b>"
    )

    texto.append("")

    texto.append(
        f"💰 Apuesta: <b>${STAKE:,} COP</b>"
        .replace(",", ".")
    )

    texto.append("")

    texto.append(
        "📊 <b>MERCADOS DETECTADOS</b>"
    )

    for nombre, probabilidad in señales:

        texto.append(
            f"{nombre}: "
            f"<b>{probabilidad:.1f}%</b>"
        )

    texto.append("")

    texto.append(
        "📌 Basado en últimos 10 partidos"
    )

    texto.append(
        f"🕐 {fecha} UTC"
    )

    texto.append("")

    texto.append(
        "⏳ Resultado: "
        "<b>PENDIENTE</b>"
    )

    texto.append("")

    texto.append(
        "⚠️ Señal estadística. "
        "No garantiza resultado."
    )

    return "\n".join(texto)


# ============================================================
# MAIN
# ============================================================

def main():

    inicio = time.time()

    print("")
    print("====================================")
    print("🚀 INICIANDO ANÁLISIS")
    print("====================================")

    partidos = obtener_partidos()

    if not partidos:

        print(
            "⚠️ No se encontraron partidos."
        )

        return

    # --------------------------------------------------------
    # FILTRAR PARTIDOS
    # --------------------------------------------------------

    partidos = partidos[
        :MAX_PARTIDOS
    ]

    print(
        f"🎯 Analizando "
        f"{len(partidos)} partidos."
    )

    actualizaciones = 0

    procesados = set()

    # --------------------------------------------------------
    # ANALIZAR
    # --------------------------------------------------------

    for partido in partidos:

        fixture_id = partido.get(
            "fixture",
            {}
        ).get(
            "id"
        )

        if fixture_id in procesados:
            continue

        procesados.add(
            fixture_id
        )

        resultado = analizar_partido(
            partido
        )

        if resultado:

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

                actualizaciones += 1

            else:

                print(
                    "ℹ️ Sin señal >= 70%"
                )

        # Pequeña pausa
        time.sleep(1)

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    tiempo = (
        time.time() -
        inicio
    )

    print("")
    print("====================================")
    print(
        f"📨 Señales enviadas: "
        f"{actualizaciones}"
    )
    print(
        f"⏱️ Tiempo: "
        f"{tiempo:.1f} segundos"
    )
    print("====================================")
    print(
        "✅ Ejecución terminada."
    )
    print("====================================")


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    main()