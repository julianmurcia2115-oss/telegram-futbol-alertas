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
        r"[^a-z0-9+.\s]",
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

        r"bet365\s*:\s*([0-9]+(?:[.,][0-9]+)?)",

        r"cuota\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",

        r"odds?\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",

        r"cuotas?.*?([0-9]+\.[0-9]+)"
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

        r"🎯\s*resultado deseado\s*:\s*(.+)",

        r"resultado deseado\s*:\s*(.+)",

        r"🎯\s*picks?\s*:\s*(.+)"
    ]

    for patron in patrones:

        resultado = re.search(
            patron,
            texto,
            re.IGNORECASE
        )

        if resultado:

            valor = resultado.group(1).strip()

            valor = valor.split("\n")[0].strip()

            return valor

    return ""


# ============================================================
# DETECTAR MERCADO REAL DE BETMINES
# ============================================================

def identificar_mercado(texto):

    t = normalizar(texto)

    deseado = normalizar(
        extraer_resultado_deseado(texto)
    )

    # --------------------------------------------------------
    # BTTS
    # --------------------------------------------------------

    if (
        "ambos equipos anotan no" in t
        or
        "ambos equipos marcan no" in t
        or
        "ambos marcan no" in t
    ):

        return "BTTS NO"

    if (
        "ambos equipos anotan si" in t
        or
        "ambos equipos marcan si" in t
        or
        "ambos marcan si" in t
    ):

        return "BTTS SI"

    # --------------------------------------------------------
    # RESULTADO DESEADO BTTS
    # --------------------------------------------------------

    if (
        "ambos equipos anotan no" in deseado
        or
        "ambos equipos marcan no" in deseado
    ):

        return "BTTS NO"

    if (
        "ambos equipos anotan si" in deseado
        or
        "ambos equipos marcan si" in deseado
    ):

        return "BTTS SI"

    # --------------------------------------------------------
    # MÁS / MENOS GOLES
    # --------------------------------------------------------

    patrones_goles = [

        (
            r"(mas|over)\s*de?\s*0[.,]5",
            "Más de 0.5 goles"
        ),

        (
            r"(mas|over)\s*de?\s*1[.,]5",
            "Más de 1.5 goles"
        ),

        (
            r"(mas|over)\s*de?\s*2[.,]5",
            "Más de 2.5 goles"
        ),

        (
            r"(mas|over)\s*de?\s*3[.,]5",
            "Más de 3.5 goles"
        ),

        (
            r"(mas|over)\s*de?\s*4[.,]5",
            "Más de 4.5 goles"
        ),

        (
            r"(menos|under)\s*de?\s*0[.,]5",
            "Menos de 0.5 goles"
        ),

        (
            r"(menos|under)\s*de?\s*1[.,]5",
            "Menos de 1.5 goles"
        ),

        (
            r"(menos|under)\s*de?\s*2[.,]5",
            "Menos de 2.5 goles"
        ),

        (
            r"(menos|under)\s*de?\s*3[.,]5",
            "Menos de 3.5 goles"
        ),

        (
            r"(menos|under)\s*de?\s*4[.,]5",
            "Menos de 4.5 goles"
        )
    ]

    for patron, nombre in patrones_goles:

        if re.search(
            patron,
            t
        ):

            return nombre

    # --------------------------------------------------------
    # SIGNOS +2.5 / -2.5
    # --------------------------------------------------------

    for linea, nombre in [
        ("+0.5", "Más de 0.5 goles"),
        ("+1.5", "Más de 1.5 goles"),
        ("+2.5", "Más de 2.5 goles"),
        ("+3.5", "Más de 3.5 goles"),
        ("+4.5", "Más de 4.5 goles"),
        ("-0.5", "Menos de 0.5 goles"),
        ("-1.5", "Menos de 1.5 goles"),
        ("-2.5", "Menos de 2.5 goles"),
        ("-3.5", "Menos de 3.5 goles"),
        ("-4.5", "Menos de 4.5 goles")
    ]:

        if linea in t:

            return nombre

    # --------------------------------------------------------
    # EMPATE PRIMER TIEMPO
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
    # DOBLE OPORTUNIDAD
    # --------------------------------------------------------

    if (
        "doble oportunidad" in t
        or
        "double chance" in t
    ):

        if (
            "1x" in deseado
            or
            "local o empate" in deseado
        ):

            return "Doble oportunidad 1X"

        if (
            "x2" in deseado
            or
            "empate o visitante" in deseado
        ):

            return "Doble oportunidad X2"

        if (
            "12" in deseado
            or
            "local o visitante" in deseado
        ):

            return "Doble oportunidad 12"

        return "Doble oportunidad"

    # --------------------------------------------------------
    # 1X2
    # --------------------------------------------------------

    if (
        "1x2" in t
        or
        "resultado final" in t
        or
        "ganador del partido" in t
        or
        "match winner" in t
    ):

        if (
            deseado == "local"
            or
            deseado == "1"
            or
            "gana local" in deseado
        ):

            return "1X2 - Local"

        if (
            deseado == "empate"
            or
            deseado == "x"
            or
            "draw" in deseado
        ):

            return "1X2 - Empate"

        if (
            deseado == "visitante"
            or
            deseado == "2"
            or
            "gana visitante" in deseado
        ):

            return "1X2 - Visitante"

        return "1X2"

    # --------------------------------------------------------
    # SI EL RESULTADO DESEADO ES CLARO
    # --------------------------------------------------------

    if deseado:

        if "mas de" in deseado:
            return deseado.title()

        if "menos de" in deseado:
            return deseado.title()

        if "over" in deseado:
            return deseado.title()

        if "under" in deseado:
            return deseado.title()

    # --------------------------------------------------------
    # FALLBACK
    # --------------------------------------------------------

    # MUY IMPORTANTE:
    # Nunca convertir automáticamente una alerta desconocida
    # en BTTS.

    linea_deseada = extraer_resultado_deseado(
        texto
    )

    if linea_deseada:

        return linea_deseada[:80]

    return "Mercado no identificado"


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

        # Mercado REAL
        "mercado":
            mercado,

        # Se conserva estrategia
        # para compatibilidad
        "estrategia":
            mercado,

        "resultado_deseado":
            extraer_resultado_deseado(
                texto
            ),

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
                "mercado",
                apuesta.get(
                    "estrategia"
                )
            )
            ==
            nueva.get(
                "mercado"
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
# BOTONES DE UNA APUESTA
# ============================================================

def botones_apuesta(
    apuesta
):

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

    cuota_texto = ""

    if apuesta.get("cuota") is not None:

        cuota_texto = (
            f"💵 Cuota: "
            f"{apuesta['cuota']:.2f}\n"
        )

    mensaje = (

        "📩 <b>NUEVA APUESTA</b>\n\n"

        f"⚽ {apuesta['home']} - "
        f"{apuesta['away']}\n\n"

        f"🏆 {apuesta['liga']}\n"

        f"🎯 {apuesta['mercado']}\n"

        f"{cuota_texto}"

        f"💰 Apuesta: "
        f"${STAKE:,.0f} COP\n"

        f"📌 Estado: 🟡 PENDIENTE"
    )

    enviar(
        mensaje,
        chat_id,
        botones_apuesta(apuesta)
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
        f"⚽ {nueva['home']} - "
        f"{nueva['away']}"
    )

    print(
        f"🎯 MERCADO: "
        f"{nueva['mercado']}"
    )

    print(
        f"💵 CUOTA: "
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

    enviar_apuesta_con_botones(
        nueva
    )

    print(
        "✅ Apuesta registrada"
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

def buscar_fixture(
    apuesta
):

    home = apuesta.get(
        "home",
        ""
    )

    away = apuesta.get(
        "away",
        ""
    )

    if (
        not home
        or not away
        or home == "Desconocido"
        or away == "Desconocido"
    ):

        return None

    ahora = datetime.now(
        COLOMBIA_TZ
    )

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

    mercado = apuesta.get(
        "mercado",
        apuesta.get(
            "estrategia",
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

    # ========================================================
    # BTTS SI
    # ========================================================

    if mercado == "BTTS SI":

        if (
            home_goals >= 1
            and
            away_goals >= 1
        ):

            return "ganada"

        return "perdida"

    # ========================================================
    # BTTS NO
    # ========================================================

    if mercado == "BTTS NO":

        if (
            home_goals == 0
            or
            away_goals == 0
        ):

            return "ganada"

        return "perdida"

    # ========================================================
    # OVER
    # ========================================================

    patron = re.search(
        r"mas de\s*([0-9]+(?:[.,][0-9]+)?)",
        normalizar(mercado)
    )

    if not patron:

        patron = re.search(
            r"over\s*([0-9]+(?:[.,][0-9]+)?)",
            normalizar(mercado)
        )

    if patron:

        linea = float(
            patron.group(1)
            .replace(",", ".")
        )

        return (
            "ganada"
            if total > linea
            else "perdida"
        )

    # ========================================================
    # UNDER
    # ========================================================

    patron = re.search(
        r"menos de\s*([0-9]+(?:[.,][0-9]+)?)",
        normalizar(mercado)
    )

    if not patron:

        patron = re.search(
            r"under\s*([0-9]+(?:[.,][0-9]+)?)",
            normalizar(mercado)
        )

    if patron:

        linea = float(
            patron.group(1)
            .replace(",", ".")
        )

        return (
            "ganada"
            if total < linea
            else "perdida"
        )

    # ========================================================
    # EMPATE 1T
    # ========================================================

    if mercado == "Empate 1T":

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

    # ========================================================
    # 1X2
    # ========================================================

    if mercado == "1X2 - Local":

        return (
            "ganada"
            if home_goals > away_goals
            else "perdida"
        )

    if mercado == "1X2 - Empate":

        return (
            "ganada"
            if home_goals == away_goals
            else "perdida"
        )

    if mercado == "1X2 - Visitante":

        return (
            "ganada"
            if away_goals > home_goals
            else "perdida"
        )

    # ========================================================
    # DOBLE OPORTUNIDAD
    # ========================================================

    if mercado == "Doble oportunidad 1X":

        return (
            "ganada"
            if home_goals >= away_goals
            else "perdida"
        )

    if mercado == "Doble oportunidad X2":

        return (
            "ganada"
            if away_goals >= home_goals
            else "perdida"
        )

    if mercado == "Doble oportunidad 12":

        return (
            "ganada"
            if home_goals != away_goals
            else "perdida"
        )

    # ========================================================
    # MERCADO DESCONOCIDO
    # ========================================================

    print(
        f"⚠️ Mercado sin regla automática: "
        f"{mercado}"
    )

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

        return round(
            STAKE * (cuota - 1),
            2
        )

    except Exception:

        print(
            "⚠️ Apuesta ganada "
            "sin cuota válida"
        )

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

    return apuesta


# ============================================================
# PROCESAR BOTÓN GANADA / PERDIDA
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
                    "⚠️ Ya está cerrada",

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
            f"💵 Cuota: {float(cuota):.2f}\n"
        )

    mensaje = (

        f"{icono} "
        f"<b>APUESTA CERRADA</b>\n\n"

        f"⚽ {encontrada['home']} - "
        f"{encontrada['away']}\n\n"

        f"🏆 {encontrada['liga']}\n"

        f"🎯 {encontrada['mercado']}\n"

        f"{cuota_texto}"

        f"💰 Apuesta: "
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
                        {
                            "inline_keyboard": [
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

        fixture = buscar_fixture(
            apuesta
        )

        if not fixture:

            print(
                f"⏳ No encontrado: "
                f"{apuesta['home']} "
                f"vs "
                f"{apuesta['away']}"
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
            f"📌 {apuesta['home']} "
            f"vs {apuesta['away']} "
            f"→ {status}"
        )

        estados_finales = {
            "FT",
            "AET",
            "PEN"
        }

        if status not in estados_finales:

            continue

        resultado = determinar_resultado(
            apuesta,
            fixture
        )

        if resultado is None:

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
            texto = "GANADA"

        else:

            icono = "🔴"
            texto = "PERDIDA"

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

            f"{icono} "
            f"<b>APUESTA CERRADA</b>\n\n"

            f"⚽ {apuesta['home']} - "
            f"{apuesta['away']}\n\n"

            f"🏆 {apuesta['liga']}\n"

            f"🎯 {apuesta['mercado']}\n"

            f"{cuota_texto}"

            f"📊 Resultado: "
            f"{goals.get('home')} - "
            f"{goals.get('away')}\n"

            f"📌 Estado: "
            f"<b>{texto}</b>\n"

            f"💵 Resultado económico: "
            f"${apuesta['ganancia']:,.0f} COP"
        )

        enviar(
            mensaje,
            CHAT_ID,
            {
                "inline_keyboard": [
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
        )

    if cambios:

        guardar_apuestas(
            apuestas
        )

        print(
            "💾 signals.json actualizado"
        )


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
# PERÍODOS
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

def estadisticas_mercados(
    apuestas
):

    datos = {}

    for apuesta in apuestas:

        mercado = apuesta.get(
            "mercado"
        )

        # Compatibilidad con apuestas antiguas
        if not mercado:

            mercado = apuesta.get(
                "estrategia",
                "Mercado no identificado"
            )

        if mercado not in datos:

            datos[mercado] = {

                "total": 0,

                "ganadas": 0,

                "perdidas": 0,

                "pendientes": 0,

                "ganancia": 0
            }

        datos[mercado]["total"] += 1

        resultado = apuesta.get(
            "resultado",
            "pendiente"
        )

        if resultado == "ganada":

            datos[mercado]["ganadas"] += 1

            datos[mercado]["ganancia"] += (
                float(
                    apuesta.get(
                        "ganancia",
                        0
                    )
                )
            )

        elif resultado == "perdida":

            datos[mercado]["perdidas"] += 1

            datos[mercado]["ganancia"] += (
                float(
                    apuesta.get(
                        "ganancia",
                        -STAKE
                    )
                )
            )

        else:

            datos[mercado]["pendientes"] += 1

    return datos


# ============================================================
# PANEL PRINCIPAL
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

        "💰 <b>Apuesta:</b> "
        "$5.000 COP\n\n"

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
# PANEL DE MERCADOS
# ============================================================

def crear_panel_mercados():

    apuestas = cargar_apuestas()

    datos = estadisticas_mercados(
        apuestas
    )

    if not datos:

        return (
            "🏆 <b>ESTRATEGIAS / MERCADOS</b>\n\n"
            "Todavía no hay apuestas."
        )

    mensaje = (
        "🏆 <b>ESTRATEGIAS / MERCADOS</b>\n\n"
    )

    posicion = 1

    # Ordenar por cantidad de apuestas
    ordenados = sorted(
        datos.items(),
        key=lambda x: (
            x[1]["total"],
            x[1]["ganancia"]
        ),
        reverse=True
    )

    for mercado, d in ordenados:

        cerradas = (
            d["ganadas"] +
            d["perdidas"]
        )

        if cerradas:

            efectividad = (
                d["ganadas"] /
                cerradas
            ) * 100

            roi = (
                d["ganancia"] /
                (cerradas * STAKE)
            ) * 100

        else:

            efectividad = 0
            roi = 0

        mensaje += (

            f"<b>{posicion}. {mercado}</b>\n"

            f"   🎯 Apuestas: "
            f"{d['total']}\n"

            f"   🟢 Ganadas: "
            f"{d['ganadas']}\n"

            f"   🔴 Perdidas: "
            f"{d['perdidas']}\n"

            f"   🟡 Pendientes: "
            f"{d['pendientes']}\n"

            f"   📈 Efectividad: "
            f"{efectividad:.1f}%\n"

            f"   📊 ROI: "
            f"{roi:.2f}%\n"

            f"   💵 Resultado: "
            f"${d['ganancia']:,.0f} COP\n\n"
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
                f"💵 Cuota: {float(cuota):.2f}\n"
            )

        mensaje += (

            f"🆔 {apuesta['id']}\n"

            f"⚽ {apuesta['home']} - "
            f"{apuesta['away']}\n"

            f"🎯 {apuesta.get('mercado', 'Mercado')}\n"

            f"{cuota_texto}"

            f"💰 $5.000 COP\n\n"
        )

    return mensaje


# ============================================================
# BOTONES DEL PANEL
# ============================================================

def botones_panel():

    return {

        "inline_keyboard": [

            [

                {
                    "text":
                        "📊 Actualizar",

                    "callback_data":
                        "panel"
                },

                {
                    "text":
                        "🏆 Mercados",

                    "callback_data":
                        "mercados"
                }

            ],

            [

                {
                    "text":
                        "🟡 Pendientes",

                    "callback_data":
                        "pendientes"
                }

            ]
        ]
    }


# ============================================================
# ENVIAR PANEL
# ============================================================

def enviar_panel(
    chat_id
):

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
    # RESPUESTA DEL BOTÓN
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

    # --------------------------------------------------------
    # MERCADOS
    # --------------------------------------------------------

    elif data == "mercados":

        enviar(
            crear_panel_mercados(),
            chat_id,
            botones_panel()
        )

    # --------------------------------------------------------
    # COMPATIBILIDAD
    # --------------------------------------------------------

    elif data == "estrategias":

        enviar(
            crear_panel_mercados(),
            chat_id,
            botones_panel()
        )

    # --------------------------------------------------------
    # PENDIENTES
    # --------------------------------------------------------

    elif data == "pendientes":

        enviar(
            crear_pendientes(),
            chat_id,
            botones_panel()
        )


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

            "Bot conectado correctamente.\n\n"

            "📊 /panel\n"
            "🏆 /mercados\n"
            "🟡 /pendientes",

            chat_id,

            botones_panel()
        )

    elif comando == "/panel":

        enviar_panel(
            chat_id
        )

    elif comando in (
        "/mercados",
        "/estrategias"
    ):

        enviar(
            crear_panel_mercados(),
            chat_id,
            botones_panel()
        )

    elif comando == "/pendientes":

        enviar(
            crear_pendientes(),
            chat_id,
            botones_panel()
        )


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

    registrar_apuesta(
        texto
    )


# ============================================================
# LEER TELEGRAM
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