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


def enviar(mensaje, chat_id=None):

    if chat_id is None:
        chat_id = CHAT_ID

    return telegram_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": mensaje,
            "parse_mode": "HTML"
        }
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
        r"[^a-z0-9\s\.\+\-]",
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

    if not palabras_a or not palabras_b:
        return False

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
# EXTRAER ESTRATEGIA DE BETMINES
# ============================================================

def identificar_estrategia(texto):

    # --------------------------------------------------------
    # PRIORIDAD 1:
    # Resultado deseado de BetMines
    # --------------------------------------------------------

    patrones = [

        r"🎯\s*Resultado deseado\s*:\s*(.+)",

        r"Resultado\s*deseado\s*:\s*(.+)",

        r"🎯\s*Pick\s*:\s*(.+)",

        r"Pick\s*:\s*(.+)",

        r"Selección\s*:\s*(.+)",

        r"Seleccion\s*:\s*(.+)"
    ]

    for patron in patrones:

        resultado = re.search(
            patron,
            texto,
            re.IGNORECASE
        )

        if resultado:

            estrategia = resultado.group(1).strip()

            estrategia = estrategia.split(
                "\n"
            )[0].strip()

            estrategia = re.sub(
                r"[🟢🔴🟡🔵⚽🎯📈💰🎳]+",
                "",
                estrategia
            ).strip()

            if estrategia:

                return estrategia

    # --------------------------------------------------------
    # Si no encuentra Resultado deseado,
    # buscar mercados conocidos directamente
    # --------------------------------------------------------

    lineas = texto.splitlines()

    for linea in lineas:

        linea_limpia = linea.strip()

        if not linea_limpia:
            continue

        if re.search(
            r"ambos equipos marcan",
            linea_limpia,
            re.IGNORECASE
        ):

            return linea_limpia

        if re.search(
            r"mas de\s*[0-9]+(?:\.[0-9]+)?",
            normalizar(linea_limpia),
            re.IGNORECASE
        ):

            return linea_limpia

        if re.search(
            r"menos de\s*[0-9]+(?:\.[0-9]+)?",
            normalizar(linea_limpia),
            re.IGNORECASE
        ):

            return linea_limpia

    return "Otra"


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

        # BetMines:
        # 🟢 bet365: 1.66
        r"bet365\s*:\s*([0-9]+(?:[.,][0-9]+)?)",

        # Cualquier casa:
        # betxxxx: 1.80
        r"bet[a-zA-Z0-9_]*\s*:\s*([0-9]+(?:[.,][0-9]+)?)",

        # Cuota: 1.66
        r"cuota\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",

        # Odds: 1.66
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
# BOTONES DE RESULTADO
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

        f"🎯 {apuesta['estrategia']}\n"

        f"{cuota_texto}"

        f"💰 Apuesta: "
        f"${STAKE:,.0f} COP\n"

        f"📌 Estado: 🟡 PENDIENTE"
    )

    keyboard = {

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

            ]
        ]
    }

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
                    keyboard,
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
        "📩 NUEVA ALERTA BETMINES"
    )

    print(
        f"⚽ Partido: "
        f"{nueva['home']} - "
        f"{nueva['away']}"
    )

    print(
        f"🎯 Estrategia: "
        f"{nueva['estrategia']}"
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
# RESULTADO DE LA APUESTA
# ============================================================

def determinar_resultado(
    apuesta,
    fixture
):

    estrategia_original = apuesta.get(
        "estrategia",
        ""
    )

    estrategia = normalizar(
        estrategia_original
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

    # ========================================================
    # BTTS SI
    # ========================================================

    if (

        "ambos equipos marcan si"
        in estrategia

        or
        "ambos marcan si"
        in estrategia

        or
        estrategia == "btts si"

        or
        estrategia == "btts"

    ):

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

    if (

        "ambos equipos marcan no"
        in estrategia

        or
        "ambos marcan no"
        in estrategia

        or
        estrategia == "btts no"

    ):

        if (

            home_goals == 0
            or
            away_goals == 0

        ):

            return "ganada"

        return "perdida"

    # ========================================================
    # MÁS DE X GOLES
    # ========================================================

    patron_over = re.search(
        r"(?:mas de|over)\s*(\d+(?:\.\d+)?)",
        estrategia
    )

    if patron_over:

        linea = float(
            patron_over.group(1)
        )

        if total > linea:

            return "ganada"

        return "perdida"

    # ========================================================
    # MENOS DE X GOLES
    # ========================================================

    patron_under = re.search(
        r"(?:menos de|under)\s*(\d+(?:\.\d+)?)",
        estrategia
    )

    if patron_under:

        linea = float(
            patron_under.group(1)
        )

        if total < linea:

            return "ganada"

        return "perdida"

    # ========================================================
    # EMPATE PRIMER TIEMPO
    # ========================================================

    if (

        "empate 1t"
        in estrategia

        or

        "empate al descanso"
        in estrategia

        or

        "empate descanso"
        in estrategia

        or

        "half time draw"
        in estrategia

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
            else "perdida"
        )

    # ========================================================
    # 1X2 - EMPATE
    # ========================================================

    if (

        "empate"
        in estrategia

        or

        "draw"
        in estrategia

    ):

        # Evitar confundir Empate 1T
        if (
            "1t" not in estrategia
            and
            "descanso" not in estrategia
        ):

            return (

                "ganada"
                if home_goals == away_goals
                else "perdida"
            )

    # ========================================================
    # 1X2 - LOCAL
    # ========================================================

    if (

        "local"
        in estrategia

        or

        estrategia in [
            "1",
            "home",
            "local gana"
        ]

    ):

        return (

            "ganada"
            if home_goals > away_goals
            else "perdida"
        )

    # ========================================================
    # 1X2 - VISITANTE
    # ========================================================

    if (

        "visitante"
        in estrategia

        or

        estrategia in [
            "2",
            "away",
            "visitante gana"
        ]

    ):

        return (

            "ganada"
            if away_goals > home_goals
            else "perdida"
        )

    # ========================================================
    # NO SE PUDO IDENTIFICAR
    # ========================================================

    print(
        "⚠️ Estrategia no reconocida:"
    )

    print(
        estrategia_original
    )

    return None


# ============================================================
# CALCULAR GANANCIA SEGÚN CUOTA
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

            ganancia = (
                STAKE *
                (cuota - 1)
            )

            return round(
                ganancia,
                2
            )

    except Exception:

        pass

    # Si no se encontró cuota,
    # no inventamos una ganancia.

    return 0


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
# PROCESAR RESULTADO MANUAL
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

        print(
            "❌ ID de apuesta inválido"
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

    if cuota:

        cuota_texto = (
            f"💵 Cuota: {float(cuota):.2f}\n"
        )

    else:

        cuota_texto = (
            "💵 Cuota: No encontrada\n"
        )

    mensaje = (

        f"{icono} "
        f"<b>APUESTA CERRADA</b>\n\n"

        f"⚽ {encontrada['home']} - "
        f"{encontrada['away']}\n\n"

        f"🏆 {encontrada['liga']}\n"

        f"🎯 {encontrada['estrategia']}\n"

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
                    "HTML"
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
                "⚠️ No se pudo "
                "determinar el resultado"
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

        apuesta["resultado_manual"] = (
            False
        )

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

        else:

            icono = "🔴"

        cuota = apuesta.get(
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

            f"⚽ {apuesta['home']} - "
            f"{apuesta['away']}\n\n"

            f"🎯 {apuesta['estrategia']}\n"

            f"{cuota_texto}"

            f"📊 Resultado: "
            f"{goals.get('home')} - "
            f"{goals.get('away')}\n"

            f"📌 Estado: "
            f"{resultado.upper()}\n"

            f"💵 Resultado: "
            f"${apuesta['ganancia']:,.0f} COP"
        )

        enviar(
            mensaje
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
# ESTADÍSTICAS DINÁMICAS DE ESTRATEGIAS
# ============================================================

def estrategias(apuestas):

    datos = {}

    for apuesta in apuestas:

        nombre = apuesta.get(
            "estrategia",
            "Otra"
        )

        nombre = str(
            nombre
        ).strip()

        if not nombre:

            nombre = "Otra"

        if nombre not in datos:

            datos[nombre] = {

                "total":
                    0,

                "ganadas":
                    0,

                "perdidas":
                    0,

                "pendientes":
                    0,

                "ganancia":
                    0
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

    for nombre, datos_estrategia in datos.items():

        cerradas = (

            datos_estrategia["ganadas"]

            +

            datos_estrategia["perdidas"]

        )

        if cerradas:

            efectividad = (

                datos_estrategia["ganadas"]

                /

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

                datos_estrategia["ganancia"]

                /

                total_invertido

            ) * 100

        else:

            roi = 0

        resultado.append(
            (
                nombre,
                datos_estrategia,
                efectividad,
                roi
            )
        )

    resultado.sort(
        key=lambda x: (
            x[2],
            x[1]["ganancia"]
        ),
        reverse=True
    )

    return resultado


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
# PANEL DE ESTRATEGIAS
# ============================================================

def crear_panel_estrategias():

    apuestas = cargar_apuestas()

    datos = estrategias(
        apuestas
    )

    if not datos:

        return (
            "🏆 <b>ESTRATEGIAS</b>\n\n"
            "Todavía no hay estrategias."
        )

    mensaje = (
        "🏆 <b>ESTRATEGIAS</b>\n\n"
    )

    posicion = 1

    for (
        nombre,
        datos_estrategia,
        efectividad,
        roi
    ) in datos:

        mensaje += (

            f"{posicion}. "
            f"<b>{nombre}</b>\n"

            f"   🎯 Apuestas: "
            f"{datos_estrategia['total']}\n"

            f"   🟢 Ganadas: "
            f"{datos_estrategia['ganadas']}\n"

            f"   🔴 Perdidas: "
            f"{datos_estrategia['perdidas']}\n"

            f"   🟡 Pendientes: "
            f"{datos_estrategia['pendientes']}\n"

            f"   📈 Efectividad: "
            f"{efectividad:.1f}%\n"

            f"   📊 ROI: "
            f"{roi:.2f}%\n"

            f"   💵 Resultado: "
            f"${datos_estrategia['ganancia']:,.0f} COP\n\n"
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

    for apuesta in pendientes[-15:]:

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

            f"🎯 {apuesta['estrategia']}\n"

            f"{cuota_texto}"

            f"💰 $5.000 COP\n\n"
        )

    return mensaje


# ============================================================
# BOTONES DEL PANEL
# ============================================================

def enviar_panel(
    chat_id
):

    texto = crear_panel()

    keyboard = {

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
                        "🏆 Estrategias",

                    "callback_data":
                        "estrategias"
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

    telegram_api(
        "sendMessage",
        {

            "chat_id":
                chat_id,

            "text":
                texto,

            "parse_mode":
                "HTML",

            "reply_markup":
                json.dumps(
                    keyboard,
                    ensure_ascii=False
                )
        }
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
    # RESPUESTA GENERAL
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
    # ESTRATEGIAS
    # --------------------------------------------------------

    elif data == "estrategias":

        enviar(
            crear_panel_estrategias(),
            chat_id
        )

    # --------------------------------------------------------
    # PENDIENTES
    # --------------------------------------------------------

    elif data == "pendientes":

        enviar(
            crear_pendientes(),
            chat_id
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
    )

    if comando == "/start":

        enviar(

            "⚽ <b>FOOTBALL ALERTS</b>\n\n"

            "Bot conectado correctamente.\n\n"

            "📊 /panel\n"
            "🏆 /estrategias\n"
            "🟡 /pendientes",

            chat_id
        )

    elif comando == "/panel":

        enviar_panel(
            chat_id
        )

    elif comando == "/estrategias":

        enviar(
            crear_panel_estrategias(),
            chat_id
        )

    elif comando == "/pendientes":

        enviar(
            crear_pendientes(),
            chat_id
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