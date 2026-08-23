import os
import json
import re
import time
import requests
from datetime import datetime, timezone, timedelta

# ============================================================
# CONFIGURACIÓN
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

SIGNALS_FILE = "signals.json"
STATE_FILE = "bot_state.json"

STAKE = 5000

COLOMBIA_TZ = timezone(timedelta(hours=-5))

API_URL = "https://v3.football.api-sports.io"

POLL_SECONDS = 20


# ============================================================
# VALIDACIÓN
# ============================================================

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADO")
    raise SystemExit(1)

if not CHAT_ID:
    print("❌ TELEGRAM_CHAT_ID NO CONFIGURADO")
    raise SystemExit(1)

if not API_FOOTBALL_KEY:
    print("❌ API_FOOTBALL_KEY NO CONFIGURADO")
    raise SystemExit(1)

print("====================================")
print("⚽ FOOTBALL ALERTS")
print("====================================")
print("🤖 Telegram: OK")
print("💬 Chat ID: OK")
print("⚽ API-Football: OK")
print("💰 Apuesta: $5.000 COP")
print("🇨🇴 Zona horaria: Colombia")
print("====================================")


# ============================================================
# JSON
# ============================================================

def cargar_json(archivo, defecto):

    try:
        if not os.path.exists(archivo):
            return defecto

        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception as e:

        print(f"⚠️ Error leyendo {archivo}: {e}")
        return defecto


def guardar_json(archivo, datos):

    temporal = archivo + ".tmp"

    with open(
        temporal,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            datos,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temporal,
        archivo
    )


# ============================================================
# APUESTAS
# ============================================================

def cargar_apuestas():

    datos = cargar_json(
        SIGNALS_FILE,
        []
    )

    if isinstance(datos, list):
        return datos

    if isinstance(datos, dict):

        if "signals" in datos:
            return datos["signals"]

        if "apuestas" in datos:
            return datos["apuestas"]

    return []


def guardar_apuestas(apuestas):

    guardar_json(
        SIGNALS_FILE,
        apuestas
    )


# ============================================================
# ESTADO
# ============================================================

def cargar_estado():

    estado = cargar_json(
        STATE_FILE,
        {}
    )

    if not isinstance(estado, dict):
        estado = {}

    return estado


def guardar_estado(estado):

    guardar_json(
        STATE_FILE,
        estado
    )


# ============================================================
# TELEGRAM
# ============================================================

def telegram_api(method, data=None):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/{method}"
    )

    try:

        response = requests.post(
            url,
            data=data or {},
            timeout=30
        )

        if response.status_code == 200:
            return response.json()

        print(
            f"❌ Telegram {response.status_code}: "
            f"{response.text}"
        )

    except Exception as e:

        print(
            f"❌ Error Telegram: {e}"
        )

    return None


def enviar(mensaje, chat_id=None, botones=None):

    if chat_id is None:
        chat_id = CHAT_ID

    datos = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    if botones:

        datos["reply_markup"] = json.dumps(
            botones,
            ensure_ascii=False
        )

    return telegram_api(
        "sendMessage",
        datos
    )


# ============================================================
# UTILIDADES
# ============================================================

def ahora_colombia():

    return datetime.now(
        COLOMBIA_TZ
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def normalizar(texto):

    if not texto:
        return ""

    texto = str(texto).lower()

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n"
    }

    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(
            viejo,
            nuevo
        )

    texto = re.sub(
        r"[^a-z0-9\s.+-]",
        " ",
        texto
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def nombres_equivalentes(nombre1, nombre2):

    a = normalizar(nombre1)
    b = normalizar(nombre2)

    if not a or not b:
        return False

    if a == b:
        return True

    palabras_a = set(a.split())
    palabras_b = set(b.split())

    interseccion = (
        palabras_a &
        palabras_b
    )

    minimo = min(
        len(palabras_a),
        len(palabras_b)
    )

    if minimo > 0:

        porcentaje = (
            len(interseccion) /
            minimo
        )

        if porcentaje >= 0.6:
            return True

    return (
        a in b or
        b in a
    )


# ============================================================
# IDENTIFICAR MERCADO
# ============================================================

def identificar_estrategia(texto):

    t = normalizar(texto)

    # --------------------------------------------------------
    # BTTS SI / NO
    # --------------------------------------------------------

    if (
        "resultado deseado ambos equipos anotan no"
        in t
        or
        "ambos equipos marcan no"
        in t
        or
        "ambos marcan no"
        in t
        or
        "btts no"
        in t
    ):
        return "BTTS NO"

    if (
        "resultado deseado ambos equipos anotan si"
        in t
        or
        "ambos equipos marcan si"
        in t
        or
        "ambos marcan si"
        in t
        or
        "btts si"
        in t
    ):
        return "BTTS SI"

    # --------------------------------------------------------
    # GOLES
    # --------------------------------------------------------

    mercados = [

        (
            "Más de 0.5 goles",
            [
                "mas de 0.5",
                "over 0.5",
                "+0.5"
            ]
        ),

        (
            "Más de 1.5 goles",
            [
                "mas de 1.5",
                "over 1.5",
                "+1.5"
            ]
        ),

        (
            "Más de 2.5 goles",
            [
                "mas de 2.5",
                "over 2.5",
                "+2.5"
            ]
        ),

        (
            "Más de 3.5 goles",
            [
                "mas de 3.5",
                "over 3.5",
                "+3.5"
            ]
        ),

        (
            "Más de 4.5 goles",
            [
                "mas de 4.5",
                "over 4.5",
                "+4.5"
            ]
        ),

        (
            "Menos de 0.5 goles",
            [
                "menos de 0.5",
                "under 0.5",
                "-0.5"
            ]
        ),

        (
            "Menos de 1.5 goles",
            [
                "menos de 1.5",
                "under 1.5",
                "-1.5"
            ]
        ),

        (
            "Menos de 2.5 goles",
            [
                "menos de 2.5",
                "under 2.5",
                "-2.5"
            ]
        ),

        (
            "Menos de 3.5 goles",
            [
                "menos de 3.5",
                "under 3.5",
                "-3.5"
            ]
        ),

        (
            "Menos de 4.5 goles",
            [
                "menos de 4.5",
                "under 4.5",
                "-4.5"
            ]
        ),

        (
            "Empate 1T",
            [
                "empate 1t",
                "empate al descanso",
                "empate descanso",
                "half time draw"
            ]
        )
    ]

    for nombre, palabras in mercados:

        for palabra in palabras:

            if palabra in t:
                return nombre

    # --------------------------------------------------------
    # 1X2
    # --------------------------------------------------------

    if "1x2" in t:

        if re.search(
            r"\bempate\b",
            t
        ):
            return "1X2 - Empate"

        return "1X2"

    # --------------------------------------------------------
    # OTROS MERCADOS
    # --------------------------------------------------------

    if "doble oportunidad" in t:
        return "Doble oportunidad"

    if "corner" in t or "corners" in t:
        return "Corners"

    if "tarjeta" in t or "cards" in t:
        return "Tarjetas"

    if "tiro a puerta" in t or "shots on target" in t:
        return "Tiros a puerta"

    if "gol del equipo local" in t:
        return "Gol equipo local"

    if "gol del equipo visitante" in t:
        return "Gol equipo visitante"

    return "Otro mercado"


# ============================================================
# PARTIDO
# ============================================================

def extraer_partido(texto):

    patron = re.search(
        r"🆚\s*(.+?)\s*[-–]\s*(.+?)(?:\n|$)",
        texto,
        re.IGNORECASE
    )

    if patron:

        return (
            patron.group(1).strip(),
            patron.group(2).strip()
        )

    patron = re.search(
        r"(.+?)\s+[-–]\s+(.+)",
        texto
    )

    if patron:

        return (
            patron.group(1).strip(),
            patron.group(2).strip()
        )

    return (
        "Desconocido",
        "Desconocido"
    )


# ============================================================
# LIGA
# ============================================================

def extraer_liga(texto):

    patron = re.search(
        r"🏆\s*(.+)",
        texto
    )

    if patron:
        return patron.group(1).strip()

    return "Desconocida"


# ============================================================
# FECHA
# ============================================================

def extraer_fecha(texto):

    patron = re.search(
        r"🗓\s*(.+)",
        texto
    )

    if patron:
        return patron.group(1).strip()

    return ""


# ============================================================
# CUOTA
# ============================================================

def extraer_cuota(texto):

    patrones = [

        # Bet365
        r"bet365\s*:\s*([0-9]+(?:[.,][0-9]+)?)",

        # Pinnacle
        r"pinnacle\s*:\s*([0-9]+(?:[.,][0-9]+)?)",

        # Cuota
        r"cuota\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",

        # Odds
        r"odds?\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",

        # BetMines puede mostrar "bet365: 1.66"
        r"bet365\s+([0-9]+(?:[.,][0-9]+)?)"
    ]

    for patron in patrones:

        resultado = re.search(
            patron,
            texto,
            re.IGNORECASE
        )

        if resultado:

            try:

                return float(
                    resultado.group(1)
                    .replace(",", ".")
                )

            except Exception:
                pass

    return None


# ============================================================
# CREAR APUESTA
# ============================================================

def crear_apuesta(texto):

    home, away = extraer_partido(
        texto
    )

    estrategia = identificar_estrategia(
        texto
    )

    liga = extraer_liga(
        texto
    )

    fecha_partido = extraer_fecha(
        texto
    )

    cuota = extraer_cuota(
        texto
    )

    apuesta = {

        "id": int(
            time.time() * 1000
        ),

        "fecha_registro":
            ahora_colombia(),

        "timestamp":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "home":
            home,

        "away":
            away,

        "liga":
            liga,

        "fecha_partido":
            fecha_partido,

        "estrategia":
            estrategia,

        "cuota":
            cuota,

        "stake":
            STAKE,

        "resultado":
            "pendiente",

        "resultado_manual":
            False,

        "ganancia":
            0,

        "fixture_id":
            None,

        "goles_home":
            None,

        "goles_away":
            None,

        "goles_home_ht":
            None,

        "goles_away_ht":
            None,

        "fecha_resultado":
            None,

        "texto_original":
            texto
    }

    return apuesta


# ============================================================
# DUPLICADOS
# ============================================================

def apuesta_duplicada(
    apuestas,
    nueva
):

    for apuesta in apuestas:

        if (

            normalizar(
                apuesta.get(
                    "home",
                    ""
                )
            )
            ==
            normalizar(
                nueva.get(
                    "home",
                    ""
                )
            )

            and

            normalizar(
                apuesta.get(
                    "away",
                    ""
                )
            )
            ==
            normalizar(
                nueva.get(
                    "away",
                    ""
                )
            )

            and

            apuesta.get(
                "estrategia"
            )
            ==
            nueva.get(
                "estrategia"
            )

            and

            apuesta.get(
                "fecha_partido"
            )
            ==
            nueva.get(
                "fecha_partido"
            )
        ):

            return True

    return False


# ============================================================
# BOTONES
# ============================================================

def botones_panel():

    return {

        "inline_keyboard": [

            [

                {
                    "text":
                        "📊 ABRIR PANEL",

                    "callback_data":
                        "panel"
                }

            ],

            [

                {
                    "text":
                        "🏆 ESTRATEGIAS",

                    "callback_data":
                        "estrategias"
                },

                {
                    "text":
                        "🟡 PENDIENTES",

                    "callback_data":
                        "pendientes"
                }

            ]
        ]
    }


def botones_resultado(apuesta_id):

    return {

        "inline_keyboard": [

            [

                {
                    "text":
                        "✅ GANADA",

                    "callback_data":
                        f"resultado_ganada:{apuesta_id}"
                },

                {
                    "text":
                        "❌ PERDIDA",

                    "callback_data":
                        f"resultado_perdida:{apuesta_id}"
                }

            ],

            [

                {
                    "text":
                        "📊 ABRIR PANEL",

                    "callback_data":
                        "panel"
                }

            ]
        ]
    }


# ============================================================
# ENVIAR NUEVA APUESTA
# ============================================================

def enviar_apuesta_con_botones(
    apuesta,
    chat_id=None
):

    if chat_id is None:
        chat_id = CHAT_ID

    cuota = apuesta.get(
        "cuota"
    )

    cuota_texto = ""

    if cuota is not None:

        cuota_texto = (
            f"💵 Cuota: <b>{cuota:.2f}</b>\n"
        )

    mensaje = (

        "📩 <b>NUEVA APUESTA</b>\n\n"

        f"⚽ {apuesta['home']} - "
        f"{apuesta['away']}\n\n"

        f"🏆 {apuesta['liga']}\n"

        f"🎯 {apuesta['estrategia']}\n"

        f"{cuota_texto}"

        f"💰 Apuesta: "
        f"${STAKE:,.0f} COP\n"

        f"📌 Estado: 🟡 PENDIENTE"
    )

    return enviar(

        mensaje,

        chat_id,

        botones_resultado(
            apuesta["id"]
        )
    )


# ============================================================
# REGISTRAR APUESTA
# ============================================================

def registrar_apuesta(texto):

    apuestas = cargar_apuestas()

    nueva = crear_apuesta(
        texto
    )

    if apuesta_duplicada(
        apuestas,
        nueva
    ):

        print(
            "ℹ️ Apuesta duplicada"
        )

        return False

    apuestas.append(
        nueva
    )

    guardar_apuestas(
        apuestas
    )

    print(
        "===================================="
    )

    print(
        "✅ NUEVA APUESTA REGISTRADA"
    )

    print(
        f"⚽ {nueva['home']} "
        f"vs "
        f"{nueva['away']}"
    )

    print(
        f"🎯 Mercado: "
        f"{nueva['estrategia']}"
    )

    print(
        f"💵 Cuota: "
        f"{nueva['cuota']}"
    )

    print(
        "===================================="
    )

    enviar_apuesta_con_botones(
        nueva
    )

    return True


# ============================================================
# API FOOTBALL
# ============================================================

def api_football(
    endpoint,
    params=None
):

    url = (
        API_URL +
        endpoint
    )

    headers = {
        "x-apisports-key":
            API_FOOTBALL_KEY
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=30
        )

        print(
            f"⚽ API-Football "
            f"{response.status_code}"
        )

        if response.status_code != 200:

            print(
                response.text[:1000]
            )

            return None

        data = response.json()

        errores = data.get(
            "errors"
        )

        if errores:

            print(
                f"⚠️ API errors: "
                f"{errores}"
            )

            return None

        return data.get(
            "response",
            []
        )

    except Exception as e:

        print(
            f"❌ Error API-Football: "
            f"{e}"
        )

        return None


# ============================================================
# BUSCAR FIXTURE
# ============================================================

def buscar_fixture(apuesta):

    home = apuesta.get(
        "home",
        ""
    )

    away = apuesta.get(
        "away",
        ""
    )

    if (
        not home or
        not away or
        home == "Desconocido" or
        away == "Desconocido"
    ):

        return None

    ahora = datetime.now(
        COLOMBIA_TZ
    )

    fechas = []

    for desplazamiento in range(
        -1,
        5
    ):

        fecha = (
            ahora +
            timedelta(
                days=desplazamiento
            )
        ).strftime(
            "%Y-%m-%d"
        )

        fechas.append(
            fecha
        )

    for fecha in fechas:

        fixtures = api_football(
            "/fixtures",
            {
                "date":
                    fecha,

                "timezone":
                    "America/Bogota"
            }
        )

        if not fixtures:
            continue

        for fixture in fixtures:

            equipos = fixture.get(
                "teams",
                {}
            )

            local = equipos.get(
                "home",
                {}
            ).get(
                "name",
                ""
            )

            visitante = equipos.get(
                "away",
                {}
            ).get(
                "name",
                ""
            )

            if (

                nombres_equivalentes(
                    home,
                    local
                )

                and

                nombres_equivalentes(
                    away,
                    visitante
                )
            ):

                print(
                    f"✅ PARTIDO ENCONTRADO: "
                    f"{local} vs {visitante}"
                )

                return fixture

    return None


# ============================================================
# DETERMINAR RESULTADO
# ============================================================

def determinar_resultado(
    apuesta,
    fixture
):

    estrategia = apuesta.get(
        "estrategia",
        ""
    )

    goals = fixture.get(
        "goals",
        {}
    )

    score = fixture.get(
        "score",
        {}
    )

    home_goals = goals.get(
        "home"
    )

    away_goals = goals.get(
        "away"
    )

    if (
        home_goals is None or
        away_goals is None
    ):

        return None

    total = (
        home_goals +
        away_goals
    )

    # --------------------------------------------------------
    # BTTS SI
    # --------------------------------------------------------

    if estrategia == "BTTS SI":

        if (
            home_goals >= 1
            and
            away_goals >= 1
        ):

            return "ganada"

        return "perdida"

    # --------------------------------------------------------
    # BTTS NO
    # --------------------------------------------------------

    if estrategia == "BTTS NO":

        if (
            home_goals == 0
            or
            away_goals == 0
        ):

            return "ganada"

        return "perdida"

    # --------------------------------------------------------
    # GOLES
    # --------------------------------------------------------

    if estrategia == "Más de 0.5 goles":

        return (
            "ganada"
            if total > 0
            else "perdida"
        )

    if estrategia == "Más de 1.5 goles":

        return (
            "ganada"
            if total > 1
            else "perdida"
        )

    if estrategia == "Más de 2.5 goles":

        return (
            "ganada"
            if total > 2
            else "perdida"
        )

    if estrategia == "Más de 3.5 goles":

        return (
            "ganada"
            if total > 3
            else "perdida"
        )

    if estrategia == "Más de 4.5 goles":

        return (
            "ganada"
            if total > 4
            else "perdida"
        )

    if estrategia == "Menos de 0.5 goles":

        return (
            "ganada"
            if total < 1
            else "perdida"
        )

    if estrategia == "Menos de 1.5 goles":

        return (
            "ganada"
            if total < 2
            else "perdida"
        )

    if estrategia == "Menos de 2.5 goles":

        return (
            "ganada"
            if total < 3
            else "perdida"
        )

    if estrategia == "Menos de 3.5 goles":

        return (
            "ganada"
            if total < 4
            else "perdida"
        )

    if estrategia == "Menos de 4.5 goles":

        return (
            "ganada"
            if total < 5
            else "perdida"
        )

    # --------------------------------------------------------
    # EMPATE 1T
    # --------------------------------------------------------

    if estrategia == "Empate 1T":

        ht = score.get(
            "halftime",
            {}
        )

        ht_home = ht.get(
            "home"
        )

        ht_away = ht.get(
            "away"
        )

        if (
            ht_home is None
            or
            ht_away is None
        ):

            return None

        return (
            "ganada"
            if ht_home == ht_away
            else "perdida"
        )

    return None


# ============================================================
# GANANCIA
# ============================================================

def calcular_ganancia(
    apuesta,
    resultado
):

    if resultado == "perdida":

        return -STAKE

    if resultado != "ganada":

        return 0

    cuota = apuesta.get(
        "cuota"
    )

    try:

        cuota = float(
            cuota
        )

        if cuota <= 1:
            return 0

        return round(
            STAKE * (cuota - 1),
            2
        )

    except Exception:

        return 0


# ============================================================
# CERRAR MANUAL
# ============================================================

def cerrar_apuesta_manual(
    apuesta,
    resultado
):

    apuesta["resultado"] = (
        resultado
    )

    apuesta["resultado_manual"] = True

    apuesta["ganancia"] = (
        calcular_ganancia(
            apuesta,
            resultado
        )
    )

    apuesta["fecha_resultado"] = (
        ahora_colombia()
    )


# ============================================================
# PRO