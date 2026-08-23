import os
import time
import requests
from datetime import datetime, timedelta, timezone

# ============================================================
# CONFIGURACIÓN
# ============================================================

FOOTBALL_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Si tienes un CHAT_ID como Secret, lo utiliza.
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://api.football-data.org/v4"

# Porcentaje mínimo para generar señal
MIN_PROBABILITY = 70

# Últimos partidos utilizados para el análisis
LAST_MATCHES = 10

# Tiempo máximo de espera ante HTTP 429
MAX_WAIT_429 = 65

# ============================================================
# VALIDACIÓN
# ============================================================

if not FOOTBALL_API_KEY:
    print("❌ FOOTBALL_DATA_API_KEY no está configurada.")
    raise SystemExit(1)

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN no está configurada.")
    raise SystemExit(1)

print("====================================")
print("⚽ FOOTBALL ALERTS")
print("====================================")
print("🔑 FootballData: CONFIGURADA")
print("🤖 Telegram: CONFIGURADO")
print("====================================")


# ============================================================
# SESIÓN HTTP
# ============================================================

session = requests.Session()

session.headers.update({
    "X-Auth-Token": FOOTBALL_API_KEY,
    "User-Agent": "FootballAlertsBot/1.0"
})


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensaje):
    """
    Envía un mensaje a Telegram.
    """

    if not CHAT_ID:
        print("⚠️ TELEGRAM_CHAT_ID no está configurado.")
        print("📨 Mensaje que se enviaría:")
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
            f"❌ Telegram HTTP {response.status_code}: "
            f"{response.text}"
        )

    except Exception as e:
        print(f"❌ Error Telegram: {e}")

    return False


# ============================================================
# PETICIÓN A FOOTBALL-DATA
# ============================================================

def football_get(endpoint, params=None, retries=3):
    """
    Hace una petición a football-data.org.

    Maneja automáticamente:
    - 200
    - 429
    - errores de conexión
    """

    url = BASE_URL + endpoint

    for intento in range(1, retries + 1):

        try:

            response = session.get(
                url,
                params=params,
                timeout=30
            )

            print(
                f"Football-data: "
                f"{endpoint} HTTP {response.status_code}"
            )

            # ------------------------------------------------
            # CORRECTO
            # ------------------------------------------------

            if response.status_code == 200:
                return response.json()

            # ------------------------------------------------
            # LÍMITE DE PETICIONES
            # ------------------------------------------------

            if response.status_code == 429:

                wait_time = 60

                try:
                    data = response.json()

                    message = data.get("message", "")

                    # Busca números dentro del mensaje
                    import re

                    numeros = re.findall(
                        r"\d+",
                        message
                    )

                    if numeros:
                        wait_time = int(numeros[0]) + 2

                except Exception:
                    pass

                wait_time = min(
                    wait_time,
                    MAX_WAIT_429
                )

                print(
                    f"⏳ Límite API alcanzado. "
                    f"Esperando {wait_time} segundos..."
                )

                time.sleep(wait_time)

                continue

            # ------------------------------------------------
            # TOKEN INVÁLIDO
            # ------------------------------------------------

            if response.status_code == 400:

                try:
                    data = response.json()

                    print(
                        "❌ Football-data:",
                        data
                    )

                except Exception:
                    print(
                        "❌ Football-data:",
                        response.text
                    )

                return None

            # ------------------------------------------------
            # OTROS ERRORES
            # ------------------------------------------------

            print(
                f"⚠️ Error API "
                f"{response.status_code}: "
                f"{response.text}"
            )

        except requests.exceptions.RequestException as e:

            print(
                f"⚠️ Error de conexión "
                f"(intento {intento}/{retries}): {e}"
            )

            time.sleep(5)

    return None


# ============================================================
# OBTENER PARTIDOS DEL DÍA
# ============================================================

def obtener_partidos():

    hoy = datetime.now(timezone.utc).date()

    manana = hoy + timedelta(days=1)

    print(
        f"📅 Descargando partidos "
        f"{hoy} y {manana}"
    )

    partidos = []

    # --------------------------------------------------------
    # UNA SOLA PETICIÓN PARA HOY
    # --------------------------------------------------------

    data_hoy = football_get(
        "/matches",
        params={
            "dateFrom": hoy.isoformat(),
            "dateTo": hoy.isoformat()
        }
    )

    if data_hoy:
        partidos.extend(
            data_hoy.get("matches", [])
        )

    # --------------------------------------------------------
    # UNA SOLA PETICIÓN PARA MAÑANA
    # --------------------------------------------------------

    data_manana = football_get(
        "/matches",
        params={
            "dateFrom": manana.isoformat(),
            "dateTo": manana.isoformat()
        }
    )

    if data_manana:
        partidos.extend(
            data_manana.get("matches", [])
        )

    # --------------------------------------------------------
    # ELIMINAR DUPLICADOS
    # --------------------------------------------------------

    partidos_unicos = {}

    for partido in partidos:

        partido_id = partido.get("id")

        if partido_id:
            partidos_unicos[partido_id] = partido

    resultado = list(
        partidos_unicos.values()
    )

    print(
        f"📊 Partidos disponibles: "
        f"{len(resultado)}"
    )

    return resultado


# ============================================================
# NORMALIZAR NOMBRES
# ============================================================

def normalizar_nombre(nombre):

    if not nombre:
        return ""

    nombre = nombre.lower()

    reemplazos = {
        " fc": "",
        " cf": "",
        " sc": "",
        " afc": "",
        " united": "",
        " utd": "",
        " city": "",
        " sporting": "",
        " club": ""
    }

    for viejo, nuevo in reemplazos.items():
        nombre = nombre.replace(
            viejo,
            nuevo
        )

    return (
        nombre
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


# ============================================================
# BUSCAR PARTIDO EN LA LISTA
# ============================================================

def buscar_partido(
    partidos,
    local,
    visitante
):

    local_busqueda = normalizar_nombre(local)
    visitante_busqueda = normalizar_nombre(visitante)

    for partido in partidos:

        home = partido.get(
            "homeTeam",
            {}
        ).get(
            "name",
            ""
        )

        away = partido.get(
            "awayTeam",
            {}
        ).get(
            "name",
            ""
        )

        home_normalizado = normalizar_nombre(
            home
        )

        away_normalizado = normalizar_nombre(
            away
        )

        if (
            local_busqueda in home_normalizado
            or home_normalizado in local_busqueda
        ) and (
            visitante_busqueda in away_normalizado
            or away_normalizado in visitante_busqueda
        ):

            return partido

    return None


# ============================================================
# ÚLTIMOS PARTIDOS DE UN EQUIPO
# ============================================================

def obtener_ultimos_partidos(team_id, limite=10):

    print(
        f"📈 Buscando últimos "
        f"{limite} partidos del equipo {team_id}"
    )

    fecha_final = datetime.now(
        timezone.utc
    ).date()

    fecha_inicio = (
        fecha_final -
        timedelta(days=180)
    )

    data = football_get(
        f"/teams/{team_id}/matches",
        params={
            "dateFrom": fecha_inicio.isoformat(),
            "dateTo": fecha_final.isoformat(),
            "status": "FINISHED"
        }
    )

    if not data:
        return []

    partidos = data.get(
        "matches",
        []
    )

    partidos.sort(
        key=lambda x: x.get(
            "utcDate",
            ""
        ),
        reverse=True
    )

    return partidos[:limite]


# ============================================================
# ESTADÍSTICAS BTTS
# ============================================================

def calcular_btts(partidos, team_id):

    if not partidos:
        return 0

    total = 0

    for partido in partidos:

        score = partido.get(
            "score",
            {}
        )

        fulltime = score.get(
            "fullTime",
            {}
        )

        home_goals = fulltime.get(
            "home"
        )

        away_goals = fulltime.get(
            "away"
        )

        if (
            home_goals is None
            or away_goals is None
        ):
            continue

        if (
            home_goals > 0
            and away_goals > 0
        ):
            total += 1

    return (
        total /
        len(partidos)
    ) * 100


# ============================================================
# ESTADÍSTICAS OVER 2.5
# ============================================================

def calcular_over25(partidos):

    if not partidos:
        return 0

    total = 0

    for partido in partidos:

        score = partido.get(
            "score",
            {}
        )

        fulltime = score.get(
            "fullTime",
            {}
        )

        home_goals = fulltime.get(
            "home"
        )

        away_goals = fulltime.get(
            "away"
        )

        if (
            home_goals is None
            or away_goals is None
        ):
            continue

        if (
            home_goals +
            away_goals
        ) > 2:

            total += 1

    return (
        total /
        len(partidos)
    ) * 100


# ============================================================
# EMPATE AL DESCANSO
# ============================================================

def calcular_empate_descanso(partidos):

    if not partidos:
        return 0

    total = 0

    for partido in partidos:

        score = partido.get(
            "score",
            {}
        )

        halftime = score.get(
            "halfTime",
            {}
        )

        home_goals = halftime.get(
            "home"
        )

        away_goals = halftime.get(
            "away"
        )

        if (
            home_goals is None
            or away_goals is None
        ):
            continue

        if home_goals == away_goals:
            total += 1

    return (
        total /
        len(partidos)
    ) * 100


# ============================================================
# ANALIZAR PARTIDO
# ============================================================

def analizar_partido(partido):

    home_team = partido.get(
        "homeTeam",
        {}
    )

    away_team = partido.get(
        "awayTeam",
        {}
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

        print(
            f"⚠️ Sin IDs: "
            f"{home_name} - {away_name}"
        )

        return None

    print(
        f"🔎 Analizando: "
        f"{home_name} vs {away_name}"
    )

    # --------------------------------------------------------
    # ÚLTIMOS 10 LOCAL
    # --------------------------------------------------------

    home_matches = obtener_ultimos_partidos(
        home_id,
        LAST_MATCHES
    )

    time.sleep(1)

    # --------------------------------------------------------
    # ÚLTIMOS 10 VISITANTE
    # --------------------------------------------------------

    away_matches = obtener_ultimos_partidos(
        away_id,
        LAST_MATCHES
    )

    time.sleep(1)

    if (
        len(home_matches) < 5
        or len(away_matches) < 5
    ):

        print(
            "⚠️ No hay suficientes "
            "partidos históricos."
        )

        return None

    # --------------------------------------------------------
    # CÁLCULOS
    # --------------------------------------------------------

    home_btts = calcular_btts(
        home_matches,
        home_id
    )

    away_btts = calcular_btts(
        away_matches,
        away_id
    )

    home_over25 = calcular_over25(
        home_matches
    )

    away_over25 = calcular_over25(
        away_matches
    )

    home_ht_draw = calcular_empate_descanso(
        home_matches
    )

    away_ht_draw = calcular_empate_descanso(
        away_matches
    )

    # Promedios
    btts = (
        home_btts +
        away_btts
    ) / 2

    over25 = (
        home_over25 +
        away_over25
    ) / 2

    empate_ht = (
        home_ht_draw +
        away_ht_draw
    ) / 2

    resultado = {
        "home": home_name,
        "away": away_name,
        "btts": btts,
        "over25": over25,
        "empate_ht": empate_ht
    }

    return resultado


# ============================================================
# CREAR ALERTA
# ============================================================

def crear_alerta(resultado):

    if not resultado:
        return None

    home = resultado["home"]
    away = resultado["away"]

    btts = resultado["btts"]
    over25 = resultado["over25"]
    empate_ht = resultado["empate_ht"]

    señales = []

    if btts >= MIN_PROBABILITY:

        señales.append(
            f"⚽ <b>BTTS: {btts:.1f}%</b>"
        )

    if over25 >= MIN_PROBABILITY:

        señales.append(
            f"🔥 <b>OVER 2.5: {over25:.1f}%</b>"
        )

    if empate_ht >= MIN_PROBABILITY:

        señales.append(
            f"🤝 <b>EMPATE 1T: "
            f"{empate_ht:.1f}%</b>"
        )

    if not señales:
        return None

    mensaje = (
        "🚨 <b>SEÑAL FOOTBALL ALERTS</b>\n\n"
        f"⚽ <b>{home}</b> vs "
        f"<b>{away}</b>\n\n"
        + "\n".join(señales)
        + "\n\n"
        "📊 Basado en últimos 10 partidos."
    )

    return mensaje


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

def main():

    inicio = time.time()

    print("")
    print("====================================")
    print("🚀 INICIANDO ANÁLISIS")
    print("====================================")

    # --------------------------------------------------------
    # OBTENER PARTIDOS
    # --------------------------------------------------------

    partidos = obtener_partidos()

    if not partidos:

        print(
            "⚠️ No se encontraron partidos."
        )

        return

    # --------------------------------------------------------
    # LÍMITE DE PARTIDOS
    #
    # IMPORTANTE:
    # No analizamos cientos de partidos.
    # --------------------------------------------------------

    MAX_PARTIDOS_ANALIZAR = 15

    partidos = partidos[
        :MAX_PARTIDOS_ANALIZAR
    ]

    print(
        f"🎯 Analizando máximo "
        f"{len(partidos)} partidos."
    )

    actualizaciones = 0

    partidos_procesados = set()

    # --------------------------------------------------------
    # ANALIZAR
    # --------------------------------------------------------

    for partido in partidos:

        partido_id = partido.get(
            "id"
        )

        if partido_id in partidos_procesados:
            continue

        partidos_procesados.add(
            partido_id
        )

        home = partido.get(
            "homeTeam",
            {}
        ).get(
            "name",
            ""
        )

        away = partido.get(
            "awayTeam",
            {}
        ).get(
            "name",
            ""
        )

        print("")
        print(
            f"🔎 {home} vs {away}"
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
                    "ℹ️ Sin señal >70%"
                )

        # Pequeña pausa entre partidos
        time.sleep(2)

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    tiempo = time.time() - inicio

    print("")
    print("====================================")
    print(
        f"📨 Actualizaciones: "
        f"{actualizaciones}"
    )
    print(
        f"⏱️ Tiempo: "
        f"{tiempo:.1f} segundos"
    )
    print("====================================")
    print("✅ Ejecución terminada.")
    print("====================================")


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    main()