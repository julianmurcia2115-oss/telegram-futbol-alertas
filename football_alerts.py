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

        with open(
            archivo,
            "r",
            encoding="utf-8"
        ) as f:
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
# ESTADO TELEGRAM
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

        print(f"❌ Error Telegram: {e}")

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
        r"[^a-z0-9\s+.-]",
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

    interseccion = palabras_a & palabras_b

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
# EXTRAER PARTIDO
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

    return (
        "Desconocido",
        "Desconocido"
    )


# ============================================================
# EXTRAER LIGA
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
# EXTRAER FECHA
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
# EXTRAER CUOTA
# ============================================================

def extraer_cuota(texto):

    patrones = [

        # bet365: 1.66
        r"bet365\s*:\s*([0-9]+(?:[.,][0-9]+)?)",

        # pinnacle: 1.66
        r"pinnacle\s*:\s*([0-9]+(?:[.,][0-9]+)?)",

        # cuota: 1.66
        r"cuota\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",

        # odds: 1.66
        r"odds?\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)"
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
# EXTRAER RESULTADO DESEADO
# ============================================================

def extraer_resultado_deseado(texto):

    patrones = [

        r"🎯\s*Resultado deseado\s*:\s*(.+)",

        r"Resultado deseado\s*:\s*(.+)",

        r"resultado deseado\s*=\s*(.+)"
    ]

    for patron in patrones:

        encontrado = re.search(
            patron,
            texto,
            re.IGNORECASE
        )

        if encontrado:

            valor = encontrado.group(1).strip()

            valor = valor.split("\n")[0].strip()

            return valor

    return ""


# ============================================================
# IDENTIFICACIÓN INTELIGENTE DEL MERCADO
# ============================================================

def identificar_mercado(texto):

    t = normalizar(texto)

    resultado_deseado = normalizar(
        extraer_resultado_deseado(texto)
    )

    # --------------------------------------------------------
    # BTTS
    # --------------------------------------------------------

    if (
        "ambos equipos marcan" in t
        or
        "ambos marcan" in t
        or
        "btts" in t
        or
        "both teams to score" in t
    ):

        if (
            " no" in " " + resultado_deseado
            or
            resultado_deseado.endswith("no")
        ):

            return "BTTS NO"

        if (
            " si" in " " + resultado_deseado
            or
            resultado_deseado.endswith("si")
        ):

            return "BTTS SI"

        # Si no encuentra resultado deseado,
        # revisa las cuotas SI / NO.
        if re.search(
            r"ambos equipos marcan.*no\s+[0-9]",
            t
        ):

            return "BTTS NO"

        return "BTTS"


    # --------------------------------------------------------
    # OVER / UNDER
    # --------------------------------------------------------

    patron = re.search(
        r"(\+|-)\s*([0-9]+(?:\.[0-9]+)?)",
        t
    )

    if patron:

        signo = patron.group(1)
        linea = patron.group(2)

        if signo == "+":

            return f"Más de {linea} goles"

        return f"Menos de {linea} goles"


    patrones_over = [
        r"mas de\s*([0-9]+(?:\.[0-9]+)?)",
        r"over\s*([0-9]+(?:\.[0-9]+)?)"
    ]

    for patron in patrones_over:

        encontrado = re.search(
            patron,
            t
        )

        if encontrado:

            return (
                f"Más de "
                f"{encontrado.group(1)} goles"
            )


    patrones_under = [
        r"menos de\s*([0-9]+(?:\.[0-9]+)?)",
        r"under\s*([0-9]+(?:\.[0-9]+)?)"
    ]

    for patron in patrones_under:

        encontrado = re.search(
            patron,
            t
        )

        if encontrado:

            return (
                f"Menos de "
                f"{encontrado.group(1)} goles"
            )


    # --------------------------------------------------------
    # 1X2
    # --------------------------------------------------------

    if "1x2" in t:

        if (
            "empate" in resultado_deseado
            or
            resultado_deseado == "x"
        ):
            return "1X2 - Empate"

        if (
            "local" in resultado_deseado
            or
            resultado_deseado == "1"
        ):
            return "1X2 - Local"

        if (
            "visitante" in resultado_deseado
            or
            resultado_deseado == "2"
        ):
            return "1X2 - Visitante"

        return "1X2"


    # --------------------------------------------------------
    # DOBLE OPORTUNIDAD
    # --------------------------------------------------------

    if (
        "doble oportunidad" in t
        or
        "double chance" in t
    ):

        if resultado_deseado:
            return (
                f"Doble oportunidad - "
                f"{resultado_deseado.upper()}"
            )

        return "Doble oportunidad"


    # --------------------------------------------------------
    # EMPATE AL DESCANSO
    # --------------------------------------------------------

    if (
        "empate 1t" in t
        or
        "empate al descanso" in t
        or
        "empate descanso" in t
        or
        "half time draw" in t
    ):

        return "Empate 1T"


    # --------------------------------------------------------
    # HANDICAP
    # --------------------------------------------------------

    if (
        "handicap" in t
        or
        "hándicap" in texto.lower()
    ):

        if resultado_deseado:
            return (
                f"Hándicap - "
                f"{resultado_deseado.upper()}"
            )

        return "Hándicap"


    # --------------------------------------------------------
    # GOLES EQUIPO
    # --------------------------------------------------------

    if (
        "goles equipo local" in t
        or
        "team goals home" in t
    ):

        return "Goles equipo local"


    if (
        "goles equipo visitante" in t
        or
        "team goals away" in t
    ):

        return "Goles equipo visitante"


    # --------------------------------------------------------
    # CORNERS
    # --------------------------------------------------------

    if (
        "corner" in t
        or
        "corners" in t
        or
        "tiros de esquina" in t
    ):

        if resultado_deseado:

            return (
                f"Corners - "
                f"{resultado_deseado.upper()}"
            )

        return "Corners"


    # --------------------------------------------------------
    # TARJETAS
    # --------------------------------------------------------

    if (
        "tarjetas" in t
        or
        "cards" in t
        or
        "card" in t
    ):

        if resultado_deseado:

            return (
                f"Tarjetas - "
                f"{resultado_deseado.upper()}"
            )

        return "Tarjetas"


    # --------------------------------------------------------
    # PRIMER EQUIPO EN MARCAR
    # --------------------------------------------------------

    if (
        "primer equipo en marcar" in t
        or
        "first team to score" in t
    ):

        if resultado_deseado:

            return (
                f"Primer equipo en marcar - "
                f"{resultado_deseado.upper()}"
            )

        return "Primer equipo en marcar"


    # --------------------------------------------------------
    # RESULTADO DESEADO DISPONIBLE
    # --------------------------------------------------------

    if resultado_deseado:

        return resultado_deseado.upper()


    # --------------------------------------------------------
    # MERCADO GENÉRICO
    # --------------------------------------------------------

    return "OTRO MERCADO"


# ============================================================
# CREAR APUESTA
# ============================================================

def crear_apuesta(texto):

    home, away = extraer_partido(
        texto
    )

    mercado = identificar_mercado(
        texto
    )

    resultado_deseado = (
        extraer_resultado_deseado(
            texto
        )
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

        "mercado":
            mercado,

        "estrategia":
            mercado,

        "resultado_deseado":
            resultado_deseado,

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

            normalizar(
                apuesta.get(
                    "mercado",
                    apuesta.get(
                        "estrategia",
                        ""
                    )
                )
            )
            ==
            normalizar(
                nueva.get(
                    "mercado",
                    ""
                )
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

def botones_apuesta(apuesta):

    return {

        "inline_keyboard": [

            [

                {
                    "text":
                        "✅ GANADA",

                    "callback_data":
                        f"resultado_ganada:"
                        f"{apuesta['id']}"
                },

                {
                    "text":
                        "❌ PERDIDA",

                    "callback_data":
                        f"resultado_perdida:"
                        f"{apuesta['id']}"
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
# ENVIAR APUESTA
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
            f"💵 Cuota: "
            f"{cuota:.2f}\n"
        )

    mensaje = (

        "📩 <b>NUEVA APUESTA</b>\n\n"

        f"⚽ {apuesta['home']} - "
        f"{apuesta['away']}\n\n"

        f"🏆 {apuesta['liga']}\n"

        f"🎯 Mercado: "
        f"<b>{apuesta['mercado']}</b>\n"

        + (
            f"🎯 Selección: "
            f"{apuesta['resultado_deseado']}\n"
            if apuesta.get(
                "resultado_deseado"
            )
            else ""
        )

        + cuota_texto

        + f"💰 Apuesta: "
        f"${STAKE:,.0f} COP\n"

        f"📌 Estado: 🟡 PENDIENTE"
    )

    return telegram_api(
        "sendMessage",
        {

            "chat_id":
                chat_id,

            "text":
                mensaje,

            "parse_mode":
                "HTML",

            "reply_markup":
                json.dumps(
                    botones_apuesta(
                        apuesta
                    ),
                    ensure_ascii=False
                )
        }
    )


# ============================================================
# REGISTRAR APUESTA
# ============================================================

def registrar_apuesta(texto):

    apuestas = cargar_apuestas()

    nueva = crear_apuesta(
        texto
    )

    print(
        "===================================="
    )

    print(
        "📩 NUEVA ALERTA DETECTADA"
    )

    print(
        f"⚽ {nueva['home']} "
        f"- {nueva['away']}"
    )

    print(
        f"🎯 Mercado: "
        f"{nueva['mercado']}"
    )

    print(
        f"🎯 Selección: "
        f"{nueva['resultado_deseado']}"
    )

    print(
        f"💵 Cuota: "
        f"{nueva['cuota']}"
    )

    print(
        "===================================="
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
        "✅ Apuesta registrada"
    )

    enviar_apuesta_con_botones(
        nueva
    )

    return True


# ============================================================
# API-FOOTBALL
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
        4
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
# RESULTADO DE MERCADOS
# ============================================================

def determinar_resultado(
    apuesta,
    fixture
):

    mercado = normalizar(
        apuesta.get(
            "mercado",
            apuesta.get(
                "estrategia",
                ""
            )
        )
    )

    deseado = normalizar(
        apuesta.get(
            "resultado_deseado",
            ""
        )
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
        home_goals is None
        or
        away_goals is None
    ):

        return None

    total = (
        home_goals +
        away_goals
    )

    # --------------------------------------------------------
    # BTTS
    # --------------------------------------------------------

    if (
        "btts no" in mercado
        or
        (
            "ambos" in deseado
            and
            "no" in deseado
        )
    ):

        return (
            "ganada"
            if not (
                home_goals >= 1
                and
                away_goals >= 1
            )
            else
            "perdida"
        )

    if (
        "btts si" in mercado
        or
        "btts" == mercado
        or
        (
            "ambos" in deseado
            and
            "si" in deseado
        )
    ):

        return (
            "ganada"
            if (
                home_goals >= 1
                and
                away_goals >= 1
            )
            else
            "perdida"
        )


    # --------------------------------------------------------
    # OVER
    # --------------------------------------------------------

    patron = re.search(
        r"mas de\s*([0-9]+(?:\.[0-9]+)?)",
        mercado
    )

    if not patron:

        patron = re.search(
            r"over\s*([0-9]+(?:\.[0-9]+)?)",
            mercado
        )

    if patron:

        linea = float(
            patron.group(1)
        )

        return (
            "ganada"
            if total > linea
            else
            "perdida"
        )


    # --------------------------------------------------------
    # UNDER
    # --------------------------------------------------------

    patron = re.search(
        r"menos de\s*([0-9]+(?:\.[0-9]+)?)",
        mercado
    )

    if not patron:

        patron = re.search(
            r"under\s*([0-9]+(?:\.[0-9]+)?)",
            mercado
        )

    if patron:

        linea = float(
            patron.group(1)
        )

        return (
            "ganada"
            if total < linea
            else
            "perdida"
        )


    # --------------------------------------------------------
    # EMPATE 1T
    # --------------------------------------------------------

    if (
        "empate 1t" in mercado
        or
        "empate descanso" in mercado
    ):

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
            else
            "perdida"
        )


    # --------------------------------------------------------
    # 1X2
    # --------------------------------------------------------

    if "1x2" in mercado:

        if (
            "empate" in mercado
            or
            deseado == "x"
        ):

            return (
                "ganada"
                if home_goals == away_goals
                else
                "perdida"
            )

        if (
            "local" in mercado
            or
            deseado == "1"
        ):

            return (
                "ganada"
                if home_goals > away_goals
                else
                "perdida"
            )

        if (
            "visitante" in mercado
            or
            deseado == "2"
        ):

            return (
                "ganada"
                if away_goals > home_goals
                else
                "perdida"
            )


    # --------------------------------------------------------
    # OTROS MERCADOS
    # --------------------------------------------------------
    #
    # Para mercados que el código no puede determinar con
    # seguridad mediante el marcador, se dejan pendientes.
    #
    # Así NO se marcan apuestas incorrectamente.
    #

    return None


# ============================================================
# CALCULAR GANANCIA
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

        if cuota > 1:

            return round(
                STAKE *
                (cuota - 1),
                2
            )

    except Exception:
        pass

    return 0


# ============================================================
# BOTÓN PANEL
# ============================================================

def botones_panel():

    return {

        "inline_keyboard": [

            [

                {
                    "text":
                        "📊 ACTUALIZAR PANEL",

                    "callback_data":
                        "panel"
                }

            ],

            [

                {
                    "text":
                        "🏆 ESTRATEGIAS / MERCADOS",

                    "callback_data":
                        "estrategias"
                }

            ],

            [

                {
                    "text":
                        "🟡 PENDIENTES",

                    "callback_data":
                        "pendientes"
                }

            ]

        ]
    }


# ============================================================
# CERRAR APUESTA MANUAL
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

    return apuesta


# ============================================================
# RESULTADO MANUAL
# ============================================================

def procesar_resultado_manual(
    callback,
    resultado
):

    data = callback.get(
        "data",
        ""
    )

    try:

        apuesta_id = int(
            data.split(":")[1]
        )

    except Exception:

        telegram_api(
            "answerCallbackQuery",
            {
                "callback_query_id":
                    callback.get("id"),

                "text":
                    "❌ ID inválido",

                "show_alert":
                    True
            }
        )

        return

    apuestas = cargar_apuestas()

    encontrada = None

    for apuesta in apuestas:

        try:

            if int(
                apuesta.get("id")
            ) == apuesta_id:

                encontrada = apuesta
                break

        except Exception:
            continue

    if encontrada is None:

        telegram_api(
            "answerCallbackQuery",
            {
                "callback_query_id":
                    callback.get("id"),

                "text":
                    "❌ Apuesta no encontrada",

                "show_alert":
                    True
            }
        )

        return

    if encontrada.get(
        "resultado",
        "pendiente"
    ) != "pendiente":

        telegram_api(
            "answerCallbackQuery",
            {
                "callback_query_id":
                    callback.get("id"),

                "text":
                    "⚠️ Esta apuesta ya está cerrada",

                "show_alert":
                    True
            }
        )

        return

    cerrar_apuesta_manual(
        encontrada,
        resultado
    )

    guardar_apuestas(
        apuestas
    )

    if resultado == "ganada":

        icono = "🟢"
        texto_resultado = "GANADA"

    else:

        icono = "🔴"
        texto_resultado = "PERDIDA"

    cuota = encontrada.get(
        "cuota"
    )

    cuota_texto = ""

    if cuota:

        cuota_texto = (
            f"💵 Cuota: "
            f"{float(cuota):.2f}\n"
        )

    mensaje = (

        f"{icono} <b>APUESTA CERRADA</b>\n\n"

        f"⚽ {encontrada['home']} - "
        f"{encontrada['away']}\n\n"

        f"🏆 {encontrada['liga']}\n"

        f"🎯 Mercado: "
        f"<b>{encontrada.get('mercado', 'OTRO MERCADO')}</b>\n"

        + (
            f"🎯 Selección: "
            f"{encontrada.get('resultado_deseado')}\n"
            if encontrada.get(
                "resultado_deseado"
            )
            else ""
        )

        + cuota_texto

        + f"💰 Apuesta: "
        f"${STAKE:,.0f} COP\n"

        f"📌 Resultado: "
        f"<b>{texto_resultado}</b>\n"

        f"💵 Resultado económico: "
        f"${encontrada['ganancia']:,.0f} COP\n\n"

        f"🕐 {encontrada['fecha_resultado']}"
    )

    message = callback.get(
        "message",
        {}
    )

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get(
        "id"
    )

    message_id = message.get(
        "message_id"
    )

    if chat_id and message_id:

        telegram_api(
            "editMessageText",
            {
                "chat_id":
                    chat_id,

                "message_id":
                    message_id,

                "text":
                    mensaje,

                "parse_mode":
                    "HTML",

                "reply_markup":
                    json.dumps(
                        botones_panel(),
                        ensure_ascii=False
                    )
            }
        )

    telegram_api(
        "answerCallbackQuery",
        {
            "callback_query_id":
                callback.get("id"),

            "text":
                f"Resultado registrado: "
                f"{texto_resultado}"
        }
    )

    print(
        f"✅ Resultado manual: "
        f"{encontrada['home']} vs "
        f"{encontrada['away']} = "
        f"{resultado}"
    )


# ============================================================
# ACTUALIZAR RESULTADOS AUTOMÁTICOS
# ============================================================

def actualizar_resultados():

    apuestas = cargar_apuestas()

    cambios = False

    pendientes = [

        a for a in apuestas

        if a.get(
            "resultado",
            "pendiente"
        ) == "pendiente"

        and not a.get(
            "resultado_manual",
            False
        )
    ]

    print(
        f"🟡 Pendientes: "
        f"{len(pendientes)}"
    )

    for apuesta in pendientes:

        print(
            f"🔎 Buscando: "
            f"{apuesta.get('home')} "
            f"vs "
            f"{apuesta.get('away')}"
        )

        fixture = buscar_fixture(
            apuesta
        )

        if not fixture:

            print(
                "⏳ Partido todavía "
                "no encontrado"
            )

            continue

        status = fixture.get(
            "fixture",
            {}
        ).get(
            "status",
            {}
        ).get(
            "short"
        )

        print(
            f"📌 Estado: {status}"
        )

        estados_finales = {
            "FT",
            "AET",
            "PEN"
        }

        if status not in estados_finales:

            print(
                "⏳ Partido todavía "
                "no ha terminado"
            )

            continue

        resultado = determinar_resultado(
            apuesta,
            fixture
        )

        if resultado is None:

            print(
                "⚠️ Mercado no compatible "
                "con resultado automático."
            )

            print(
                f"🎯 Mercado: "
                f"{apuesta.get('mercado')}"
            )

            print(
                "➡️ Se mantiene pendiente "
                "para poder cerrarlo manualmente."
            )

            continue

        goals = fixture.get(
            "goals",
            {}
        )

        score = fixture.get(
            "score",
            {}
        )

        ht = score.get(
            "halftime",
            {}
        )

        apuesta["resultado"] = (
            resultado
        )

        apuesta["resultado_manual"] = False

        apuesta["ganancia"] = (
            calcular_ganancia(
                apuesta,
                resultado
            )
        )

        apuesta["fixture_id"] = (
            fixture.get(
                "fixture",
                {}
            ).get(
                "id"
            )
        )

        apuesta["goles_home"] = (
            goals.get("home")
        )

        apuesta["goles_away"] = (
            goals.get("away")
        )

        apuesta["goles_home_ht"] = (
            ht.get("home")
        )

        apuesta["goles_away_ht"] = (
            ht.get("away")
        )

        apuesta["fecha_resultado"] = (
            ahora_colombia()
        )

        cambios = True

        if resultado == "ganada":

            icono = "🟢"
            resultado_texto = "GANADA"

        else:

            icono = "🔴"
            resultado_texto = "PERDIDA"

        cuota = apuesta.get(
            "cuota"
        )

        cuota_texto = ""

        if cuota:

            cuota_texto = (
                f"💵 Cuota: "
                f"{float(cuota):.2f}\n"
            )

        mensaje = (

            f"{icono} <b>APUESTA CERRADA</b>\n\n"

            f"⚽ {apuesta['home']} - "
            f"{apuesta['away']}\n\n"

            f"🏆 {apuesta['liga']}\n"

            f"🎯 Mercado: "
            f"<b>{apuesta.get('mercado')}</b>\n"

            + (
                f"🎯 Selección: "
                f"{apuesta.get('resultado_deseado')}\n"
                if apuesta.get(
                    "resultado_deseado"
                )
                else ""
            )

            + cuota_texto

            + f"💰 Apuesta: "
            f"${STAKE:,.0f} COP\n"

            f"📊 Resultado: "
            f"{goals.get('home')} - "
            f"{goals.get('away')}\n"

            f"📌 Estado: "
            f"<b>{resultado_texto}</b>\n"

            f"💵 Resultado económico: "
            f"${apuesta['ganancia']:,.0f} COP"
        )

        enviar(
            mensaje,
            CHAT_ID,
            botones_panel()
        )

        print(
            f"✅ Cerrada: "
            f"{resultado}"
        )

    if cambios:

        guardar_apuestas(
            apuestas
        )

        print(
            "💾 signals.json actualizado"
        )

    else:

        print(
            "ℹ️ No hubo resultados nuevos"
        )

    return cambios


# ============================================================
# ESTADÍSTICAS
# ============================================================

def calcular_estadisticas(
    apuestas
):

    ganadas = 0
    perdidas = 0
    pendientes = 0
    ganancia = 0

    for apuesta in apuestas:

        resultado = apuesta.get(
            "resultado",
            "pendiente"
        )

        if resultado == "ganada":

            ganadas += 1

            ganancia += float(
                apuesta.get(
                    "ganancia",
                    0
                )
            )

        elif resultado == "perdida":

            perdidas += 1

            ganancia += float(
                apuesta.get(
                    "ganancia",
                    -STAKE
                )
            )

        else:

            pendientes += 1

    cerradas = (
        ganadas +
        perdidas
    )

    if cerradas:

        efectividad = (
            ganadas /
            cerradas
        ) * 100

    else:

        efectividad = 0

    total_invertido = (
        cerradas *
        STAKE
    )

    if total_invertido:

        roi = (
            ganancia /
            total_invertido
        ) * 100

    else:

        roi = 0

    return {

        "total":
            len(apuestas),

        "ganadas":
            ganadas,

        "perdidas":
            perdidas,

        "pendientes":
            pendientes,

        "ganancia":
            ganancia,

        "efectividad":
            efectividad,

        "roi":
            roi
    }


# ============================================================
# ESTADÍSTICAS POR PERÍODO
# ============================================================

def estadisticas_periodo(
    apuestas,
    dias
):

    ahora = datetime.now(
        COLOMBIA_TZ
    )

    limite = (
        ahora -
        timedelta(days=dias)
    )

    seleccionadas = []

    for apuesta in apuestas:

        fecha = apuesta.get(
            "fecha_registro"
        )

        try:

            fecha_dt = datetime.strptime(
                fecha,
                "%Y-%m-%d %H:%M:%S"
            )

            fecha_dt = fecha_dt.replace(
                tzinfo=COLOMBIA_TZ
            )

        except Exception:

            continue

        if fecha_dt >= limite:

            seleccionadas.append(
                apuesta
            )

    return calcular_estadisticas(
        seleccionadas
    )


# ============================================================
# ESTADÍSTICAS POR MERCADO
# ============================================================

def mercados(apuestas):

    datos = {}

    for apuesta in apuestas:

        nombre = apuesta.get(
            "mercado"
        )

        if not nombre:

            nombre = apuesta.get(
                "estrategia",
                "OTRO MERCADO"
            )

        if not nombre:

            nombre = "OTRO MERCADO"

        if nombre not in datos:

            datos[nombre] = {

                "total": 0,

                "ganadas": 0,

                "perdidas": 0,

                "pendientes": 0,

                "ganancia": 0
            }

        datos[nombre]["total"] += 1

        resultado = apuesta.get(
            "resultado",
            "pendiente"
        )

        if resultado == "ganada":

            datos[nombre]["ganadas"] += 1

            datos[nombre]["ganancia"] += float(
                apuesta.get(
                    "ganancia",
                    0
                )
            )

        elif resultado == "perdida":

            datos[nombre]["perdidas"] += 1

            datos[nombre]["ganancia"] += float(
                apuesta.get(
                    "ganancia",
                    -STAKE
                )
            )

        else:

            datos[nombre]["pendientes"] += 1

    resultado = []

    for nombre, info in datos.items():

        cerradas = (
            info["ganadas"] +
            info["perdidas"]
        )

        if cerradas:

            efectividad = (
                info["ganadas"] /
                cerradas
            ) * 100

            invertido = (
                cerradas *
                STAKE
            )

            roi = (
                info["ganancia"] /
                invertido
            ) * 100

        else:

            efectividad = 0
            roi = 0

        resultado.append(
            (
                nombre,
                info,
                efectividad,
                roi
            )
        )

    resultado.sort(
        key=lambda x: (
            x[1]["total"],
            x[1]["ganancia"]
        ),
        reverse=True
    )

    return resultado


# ============================================================
# PANEL
# ============================================================

def crear_panel():

    apuestas = cargar_apuestas()

    stats = calcular_estadisticas(
        apuestas
    )

    dia = estadisticas_periodo(
        apuestas,
        1
    )

    semana = estadisticas_periodo(
        apuestas,
        7
    )

    mes = estadisticas_periodo(
        apuestas,
        30
    )

    texto = (

        "📊 <b>PANEL FOOTBALL ALERTS</b>\n\n"

        "💰 <b>Apuesta base:</b> "
        "$5.000 COP\n"

        "💵 <b>Ganancia calculada con la cuota "
        "de cada alerta</b>\n\n"

        f"🎯 <b>Total:</b> "
        f"{stats['total']}\n"

        f"🟢 <b>Ganadas:</b> "
        f"{stats['ganadas']}\n"

        f"🔴 <b>Perdidas:</b> "
        f"{stats['perdidas']}\n"

        f"🟡 <b>Pendientes:</b> "
        f"{stats['pendientes']}\n\n"

        f"💵 <b>Ganancia/Pérdida:</b> "
        f"${stats['ganancia']:,.0f} COP\n"

        f"📈 <b>Efectividad:</b> "
        f"{stats['efectividad']:.1f}%\n"

        f"📊 <b>ROI:</b> "
        f"{stats['roi']:.2f}%\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        "📅 <b>HOY</b>\n"

        f"🟢 {dia['ganadas']} | "
        f"🔴 {dia['perdidas']} | "
        f"🟡 {dia['pendientes']}\n"

        f"💵 ${dia['ganancia']:,.0f} COP\n\n"

        "📅 <b>SEMANA</b>\n"

        f"🟢 {semana['ganadas']} | "
        f"🔴 {semana['perdidas']} | "
        f"🟡 {semana['pendientes']}\n"

        f"💵 ${semana['ganancia']:,.0f} COP\n\n"

        "📅 <b>MES</b>\n"

        f"🟢 {mes['ganadas']} | "
        f"🔴 {mes['perdidas']} | "
        f"🟡 {mes['pendientes']}\n"

        f"💵 ${mes['ganancia']:,.0f} COP"
    )

    return texto


# ============================================================
# PANEL MERCADOS
# ============================================================

def crear_panel_mercados():

    apuestas = cargar_apuestas()

    datos = mercados(
        apuestas
    )

    if not datos:

        return (
            "🏆 <b>ESTRATEGIAS / MERCADOS</b>\n\n"
            "Todavía no hay apuestas registradas."
        )

    mensaje = (
        "🏆 <b>ESTRATEGIAS / MERCADOS</b>\n\n"
    )

    posicion = 1

    for (
        nombre,
        info,
        efectividad,
        roi
    ) in datos:

        mensaje += (

            f"{posicion}. "
            f"<b>{nombre}</b>\n"

            f"   🎯 Apuestas: "
            f"{info['total']}\n"

            f"   🟢 Ganadas: "
            f"{info['ganadas']}\n"

            f"   🔴 Perdidas: "
            f"{info['perdidas']}\n"

            f"   🟡 Pendientes: "
            f"{info['pendientes']}\n"

            f"   📈 Efectividad: "
            f"{efectividad:.1f}%\n"

            f"   📊 ROI: "
            f"{roi:.2f}%\n"

            f"   💵 Resultado: "
            f"${info['ganancia']:,.0f} COP\n\n"
        )

        posicion += 1

    return mensaje


# ============================================================
# PENDIENTES
# ============================================================

def crear_pendientes():

    apuestas = cargar_apuestas()

    pendientes = [

        a for a in apuestas

        if a.get(
            "resultado",
            "pendiente"
        ) == "pendiente"
    ]

    if not pendientes:

        return (
            "🟡 <b>PENDIENTES</b>\n\n"
            "No hay apuestas pendientes."
        )

    mensaje = (
        "🟡 <b>APUESTAS PENDIENTES</b>\n\n"
    )

    for apuesta in pendientes[-20:]:

        cuota = apuesta.get(
            "cuota"
        )

        cuota_texto = ""

        if cuota:

            cuota_texto = (
                f"💵 Cuota: "
                f"{float(cuota):.2f}\n"
            )

        mensaje += (

            f"🆔 {apuesta['id']}\n"

            f"⚽ {apuesta['home']} - "
            f"{apuesta['away']}\n"

            f"🎯 "
            f"{apuesta.get('mercado', 'OTRO MERCADO')}\n"

            + cuota_texto

            + "💰 $5.000 COP\n\n"
        )

    return mensaje


# ============================================================
# ENVIAR PANEL
# ============================================================

def enviar_panel(chat_id):

    enviar(
        crear_panel(),
        chat_id,
        botones_panel()
    )


# ============================================================
# CALLBACK
# ============================================================

def responder_callback(
    callback
):

    data = callback.get(
        "data",
        ""
    )

    callback_id = callback.get(
        "id"
    )

    # --------------------------------------------------------
    # RESULTADO GANADA
    # --------------------------------------------------------

    if data.startswith(
        "resultado_ganada:"
    ):

        procesar_resultado_manual(
            callback,
            "ganada"
        )

        return


    # --------------------------------------------------------
    # RESULTADO PERDIDA
    # --------------------------------------------------------

    if data.startswith(
        "resultado_perdida:"
    ):

        procesar_resultado_manual(
            callback,
            "perdida"
        )

        return


    # --------------------------------------------------------
    # RESPUESTA CALLBACK
    # --------------------------------------------------------

    telegram_api(
        "answerCallbackQuery",
        {
            "callback_query_id":
                callback_id
        }
    )

    message = callback.get(
        "message",
        {}
    )

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get(
        "id"
    )

    if not chat_id:
        return


    # --------------------------------------------------------
    # PANEL
    # --------------------------------------------------------

    if data == "panel":

        enviar_panel(
            chat_id
        )

        return


    # --------------------------------------------------------
    # MERCADOS
    # --------------------------------------------------------

    if data == "estrategias":

        enviar(
            crear_panel_mercados(),
            chat_id,
            botones_panel()
        )

        return


    # --------------------------------------------------------
    # PENDIENTES
    # --------------------------------------------------------

    if data == "pendientes":

        enviar(
            crear_pendientes(),
            chat_id,
            botones_panel()
        )

        return


# ============================================================
# COMANDOS
# ============================================================

def procesar_comando(
    chat_id,
    texto
):

    comando = (
        texto.split()[0]
        .lower()
        .split("@")[0]
    )


    if comando == "/start":

        enviar(

            "⚽ <b>FOOTBALL ALERTS</b>\n\n"

            "✅ Bot conectado correctamente.\n\n"

            "📊 /panel\n"
            "🏆 /mercados\n"
            "🟡 /pendientes\n\n"

            "Las estadísticas se calculan "
            "con la cuota real de cada alerta.",

            chat_id,

            botones_panel()
        )

        return


    if comando == "/panel":

        enviar_panel(
            chat_id
        )

        return


    if comando in (
        "/mercados",
        "/estrategias"
    ):

        enviar(
            crear_panel_mercados(),
            chat_id,
            botones_panel()
        )

        return


    if comando == "/pendientes":

        enviar(
            crear_pendientes(),
            chat_id,
            botones_panel()
        )

        return


# ============================================================
# PROCESAR MENSAJE
# ============================================================

def procesar_mensaje(
    message
):

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get(
        "id"
    )

    texto = message.get(
        "text",
        ""
    )

    if not texto:
        return

    if str(chat_id) != str(CHAT_ID):

        print(
            f"⚠️ Mensaje ignorado "
            f"de chat {chat_id}"
        )

        return


    if texto.startswith("/"):

        procesar_comando(
            chat_id,
            texto
        )

        return


    # --------------------------------------------------------
    # IGNORAR MENSAJES PROPIOS DEL BOT
    # --------------------------------------------------------

    if (
        "NUEVA APUESTA" in texto
        or
        "APUESTA CERRADA" in texto
        or
        "PANEL FOOTBALL ALERTS" in texto
        or
        "ESTRATEGIAS / MERCADOS" in texto
    ):

        return


    registrar_apuesta(
        texto
    )


# ============================================================
# RECIBIR TELEGRAM
# ============================================================

def recibir_telegram():

    estado = cargar_estado()

    offset = estado.get(
        "last_update_id",
        0
    )

    if offset:

        offset += 1

    inicio = time.time()

    print(
        "📡 Escuchando Telegram..."
    )

    while (
        time.time() - inicio
        < POLL_SECONDS
    ):

        parametros = {
            "timeout": 5
        }

        if offset:

            parametros["offset"] = (
                offset
            )

        respuesta = telegram_api(
            "getUpdates",
            parametros
        )

        if not respuesta:

            time.sleep(2)

            continue

        resultados = respuesta.get(
            "result",
            []
        )

        for update in resultados:

            update_id = update.get(
                "update_id"
            )

            if update_id is not None:

                offset = (
                    update_id + 1
                )

                estado[
                    "last_update_id"
                ] = update_id

                guardar_estado(
                    estado
                )


            if (
                "callback_query"
                in update
            ):

                responder_callback(
                    update[
                        "callback_query"
                    ]
                )

            elif (
                "message"
                in update
            ):

                procesar_mensaje(
                    update["message"]
                )

        time.sleep(1)

    print(
        "📡 Fin de recepción Telegram"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "🚀 INICIO DE EJECUCIÓN"
    )

    # --------------------------------------------------------
    # 1. RECIBIR ALERTAS
    # --------------------------------------------------------

    recibir_telegram()


    # --------------------------------------------------------
    # 2. ACTUALIZAR RESULTADOS
    # --------------------------------------------------------

    print(
        "⚽ ACTUALIZANDO RESULTADOS..."
    )

    actualizar_resultados()


    # --------------------------------------------------------
    # 3. RESUMEN
    # --------------------------------------------------------

    apuestas = cargar_apuestas()

    stats = calcular_estadisticas(
        apuestas
    )

    print(
        "===================================="
    )

    print(
        f"📊 Total: "
        f"{stats['total']}"
    )

    print(
        f"🟢 Ganadas: "
        f"{stats['ganadas']}"
    )

    print(
        f"🔴 Perdidas: "
        f"{stats['perdidas']}"
    )

    print(
        f"🟡 Pendientes: "
        f"{stats['pendientes']}"
    )

    print(
        f"💵 Resultado: "
        f"${stats['ganancia']:,.0f} COP"
    )

    print(
        f"📈 Efectividad: "
        f"{stats['efectividad']:.1f}%"
    )

    print(
        f"📊 ROI: "
        f"{stats['roi']:.2f}%"
    )

    print(
        "===================================="
    )

    print(
        "✅ EJECUCIÓN TERMINADA"
    )


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":

    main()