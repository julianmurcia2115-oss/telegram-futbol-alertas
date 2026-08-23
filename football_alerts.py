import os
import re
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from html import escape

# ============================================================
# CONFIGURACIÓN
# ============================================================

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

STAKE = 5000

API_URL = "https://v3.football.api-sports.io"

DATA_FILE = "apuestas.json"

HEADERS = {
    "x-apisports-key": API_FOOTBALL_KEY
}

# ============================================================
# VALIDACIÓN
# ============================================================

print("======================================")
print("⚽ BETMINES TRACKER")
print("======================================")

if not API_FOOTBALL_KEY:
    print("❌ API_FOOTBALL_KEY NO CONFIGURADA")
    raise SystemExit(1)

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADA")
    raise SystemExit(1)

if not CHAT_ID:
    print("❌ TELEGRAM_CHAT_ID NO CONFIGURADA")
    raise SystemExit(1)

print("🔑 API-Football: CONFIGURADA")
print("🤖 Telegram: CONFIGURADO")
print("💬 Chat ID: CONFIGURADO")
print("💰 Apuesta fija: $5.000 COP")
print("======================================")

# ============================================================
# ARCHIVO DE DATOS
# ============================================================

def cargar_datos():

    if not os.path.exists(DATA_FILE):
        return {
            "apuestas": [],
            "ultimo_update_id": 0
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {
            "apuestas": [],
            "ultimo_update_id": 0
        }


def guardar_datos(datos):

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            datos,
            f,
            ensure_ascii=False,
            indent=2
        )


datos = cargar_datos()

# ============================================================
# TELEGRAM
# ============================================================

def telegram(method, params=None):

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"

    try:

        response = requests.post(
            url,
            data=params or {},
            timeout=30
        )

        if response.status_code != 200:
            print(
                f"❌ Telegram {response.status_code}: "
                f"{response.text}"
            )
            return None

        return response.json()

    except Exception as e:

        print(f"❌ Error Telegram: {e}")
        return None


def enviar(mensaje, reply_markup=None):

    params = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    if reply_markup:
        params["reply_markup"] = json.dumps(
            reply_markup
        )

    return telegram(
        "sendMessage",
        params
    )


def editar(chat_id, message_id, mensaje, reply_markup=None):

    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    if reply_markup:
        params["reply_markup"] = json.dumps(
            reply_markup
        )

    return telegram(
        "editMessageText",
        params
    )


def responder_callback(callback_id):

    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )

# ============================================================
# TECLADO PRINCIPAL
# ============================================================

def teclado_panel():

    return {
        "inline_keyboard": [

            [
                {
                    "text": "📊 Panel",
                    "callback_data": "panel"
                },
                {
                    "text": "📅 Hoy",
                    "callback_data": "hoy"
                }
            ],

            [
                {
                    "text": "📆 Semana",
                    "callback_data": "semana"
                },
                {
                    "text": "🗓 Mes",
                    "callback_data": "mes"
                }
            ],

            [
                {
                    "text": "🏆 Estrategias",
                    "callback_data": "estrategias"
                },
                {
                    "text": "🎯 Pendientes",
                    "callback_data": "pendientes"
                }
            ],

            [
                {
                    "text": "🔄 Actualizar",
                    "callback_data": "panel"
                }
            ]

        ]
    }

# ============================================================
# UTILIDADES
# ============================================================

def ahora_colombia():

    return datetime.now(
        timezone.utc
    ) - timedelta(hours=5)


def fecha_colombia():

    return ahora_colombia().date()


def parsear_fecha(texto):

    patrones = [
        r"(?:lun|mar|mié|mie|jue|vie|sáb|sab|dom),?\s+"
        r"(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})\s+"
        r"(\d{1,2}):(\d{2})",

        r"(\d{1,2})\s+([a-záéíóú]+)\s+(\d{4})\s+"
        r"(\d{1,2}):(\d{2})"
    ]

    meses = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12
    }

    texto = texto.lower()

    for patron in patrones:

        match = re.search(
            patron,
            texto,
            re.IGNORECASE
        )

        if match:

            dia = int(match.group(1))
            mes_nombre = match.group(2)
            año = int(match.group(3))
            hora = int(match.group(4))
            minuto = int(match.group(5))

            mes = meses.get(mes_nombre)

            if mes:

                return datetime(
                    año,
                    mes,
                    dia,
                    hora,
                    minuto
                )

    return None

# ============================================================
# RECONOCER ESTRATEGIA
# ============================================================

def reconocer_estrategia(texto):

    t = texto.lower()

    # --------------------------------------------------------
    # OVER / UNDER
    # --------------------------------------------------------

    patrones_over = [
        r"más de\s+([0-9]+[,.][0-9])",
        r"mas de\s+([0-9]+[,.][0-9])",
        r"over\s*([0-9]+[,.][0-9])"
    ]

    for patron in patrones_over:

        m = re.search(patron, t)

        if m:

            linea = m.group(1).replace(",", ".")

            return {
                "tipo": "over",
                "linea": float(linea),
                "nombre": f"Más de {linea} goles"
            }

    patrones_under = [
        r"menos de\s+([0-9]+[,.][0-9])",
        r"under\s*([0-9]+[,.][0-9])"
    ]

    for patron in patrones_under:

        m = re.search(patron, t)

        if m:

            linea = m.group(1).replace(",", ".")

            return {
                "tipo": "under",
                "linea": float(linea),
                "nombre": f"Menos de {linea} goles"
            }

    # --------------------------------------------------------
    # BTTS
    # --------------------------------------------------------

    if (
        "ambos equipos marcan" in t
        or "btts" in t
    ):

        if (
            re.search(r"\bsi\b", t)
            or "yes" in t
        ):

            return {
                "tipo": "btts_yes",
                "nombre": "Ambos equipos marcan - Sí"
            }

        if (
            re.search(r"\bno\b", t)
        ):

            return {
                "tipo": "btts_no",
                "nombre": "Ambos equipos marcan - No"
            }

    # --------------------------------------------------------
    # 1X2
    # --------------------------------------------------------

    if "1x2" in t:

        if re.search(r"\b1\b", t):

            return {
                "tipo": "home",
                "nombre": "Ganador Local"
            }

        if re.search(r"\b2\b", t):

            return {
                "tipo": "away",
                "nombre": "Ganador Visitante"
            }

        if re.search(r"\bx\b", t):

            return {
                "tipo": "draw",
                "nombre": "Empate"
            }

    # --------------------------------------------------------
    # EMPATE 1T
    # --------------------------------------------------------

    if (
        "empate 1t" in t
        or "empate primer tiempo" in t
        or "empate al descanso" in t
    ):

        return {
            "tipo": "ht_draw",
            "nombre": "Empate 1er tiempo"
        }

    # --------------------------------------------------------
    # ESTRATEGIA GENÉRICA
    # --------------------------------------------------------

    return {
        "tipo": "unknown",
        "nombre": "Estrategia no identificada"
    }

# ============================================================
# EXTRAER PARTIDO
# ============================================================

def extraer_partido(texto):

    patrones = [

        r"🆚\s*(.+?)\s*-\s*(.+)",

        r"🆚\s*(.+?)\s+vs\.?\s+(.+)",

        r"(.+?)\s+-\s+(.+)"
    ]

    for patron in patrones:

        m = re.search(
            patron,
            texto
        )

        if m:

            local = m.group(1).strip()
            visitante = m.group(2).strip()

            # Evitar líneas que no sean partidos
            if len(local) > 2 and len(visitante) > 2:

                return local, visitante

    return None, None

# ============================================================
# EXTRAER CUOTA
# ============================================================

def extraer_cuota(texto):

    patrones = [

        r"pinnacle\s*:\s*([0-9]+[,.][0-9]+)",

        r"cuota\s*[:=]?\s*([0-9]+[,.][0-9]+)",

        r"odd\s*[:=]?\s*([0-9]+[,.][0-9]+)"
    ]

    for patron in patrones:

        m = re.search(
            patron,
            texto,
            re.IGNORECASE
        )

        if m:

            return float(
                m.group(1).replace(",", ".")
            )

    return None

# ============================================================
# EXTRAER LIGA
# ============================================================

def extraer_liga(texto):

    m = re.search(
        r"🏆\s*(.+)",
        texto
    )

    if m:
        return m.group(1).strip()

    return "Liga no identificada"

# ============================================================
# CREAR APUESTA
# ============================================================

def procesar_alerta(texto):

    local, visitante = extraer_partido(texto)

    if not local or not visitante:

        return None, (
            "❌ No pude reconocer el partido.\n\n"
            "Reenvíame la alerta completa de BetMines."
        )

    estrategia = reconocer_estrategia(texto)

    cuota = extraer_cuota(texto)

    liga = extraer_liga(texto)

    fecha = parsear_fecha(texto)

    if not fecha:

        # Si no encuentra fecha, usa hoy
        fecha = ahora_colombia()

    apuesta = {

        "id": int(time.time() * 1000),

        "local": local,

        "visitante": visitante,

        "liga": liga,

        "estrategia": estrategia["nombre"],

        "tipo": estrategia["tipo"],

        "linea": estrategia.get("linea"),

        "cuota": cuota,

        "stake": STAKE,

        "fecha": fecha.isoformat(),

        "estado": "PENDIENTE",

        "resultado": None,

        "ganancia": 0,

        "fixture_id": None,

        "creada": datetime.now(
            timezone.utc
        ).isoformat()
    }

    return apuesta, None

# ============================================================
# RESULTADO DE APUESTA
# ============================================================

def evaluar_apuesta(apuesta, fixture):

    fixture_status = (
        fixture.get("fixture", {})
        .get("status", {})
        .get("short")
    )

    if fixture_status not in [
        "FT",
        "AET",
        "PEN"
    ]:

        return None

    score = fixture.get(
        "goals",
        {}
    )

    home_goals = score.get("home")
    away_goals = score.get("away")

    if home_goals is None or away_goals is None:
        return None

    tipo = apuesta["tipo"]

    total = home_goals + away_goals

    ganada = False

    # --------------------------------------------------------
    # OVER
    # --------------------------------------------------------

    if tipo == "over":

        linea = apuesta.get("linea")

        if linea is not None:
            ganada = total > linea

    # --------------------------------------------------------
    # UNDER
    # --------------------------------------------------------

    elif tipo == "under":

        linea = apuesta.get("linea")

        if linea is not None:
            ganada = total < linea

    # --------------------------------------------------------
    # BTTS YES
    # --------------------------------------------------------

    elif tipo == "btts_yes":

        ganada = (
            home_goals > 0
            and away_goals > 0
        )

    # --------------------------------------------------------
    # BTTS NO
    # --------------------------------------------------------

    elif tipo == "btts_no":

        ganada = (
            home_goals == 0
            or away_goals == 0
        )

    # --------------------------------------------------------
    # LOCAL
    # --------------------------------------------------------

    elif tipo == "home":

        ganada = home_goals > away_goals

    # --------------------------------------------------------
    # VISITANTE
    # --------------------------------------------------------

    elif tipo == "away":

        ganada = away_goals > home_goals

    # --------------------------------------------------------
    # EMPATE
    # --------------------------------------------------------

    elif tipo == "draw":

        ganada = home_goals == away_goals

    # --------------------------------------------------------
    # EMPATE PRIMER TIEMPO
    # --------------------------------------------------------

    elif tipo == "ht_draw":

        halftime = fixture.get(
            "score",
            {}
        ).get(
            "halftime",
            {}
        )

        ht_home = halftime.get("home")
        ht_away = halftime.get("away")

        if ht_home is None or ht_away is None:
            return None

        ganada = ht_home == ht_away

    else:

        return None

    cuota = apuesta.get("cuota")

    if ganada:

        if cuota:

            ganancia_neta = (
                apuesta["stake"] * cuota
            ) - apuesta["stake"]

        else:

            ganancia_neta = 0

        return {
            "estado": "GANADA",
            "ganancia": ganancia_neta,
            "marcador": f"{home_goals}-{away_goals}"
        }

    else:

        return {
            "estado": "PERDIDA",
            "ganancia": -apuesta["stake"],
            "marcador": f"{home_goals}-{away_goals}"
        }

# ============================================================
# API FOOTBALL
# ============================================================

def api_get(endpoint, params=None):

    try:

        response = requests.get(
            API_URL + endpoint,
            headers=HEADERS,
            params=params or {},
            timeout=30
        )

        print(
            f"API-Football: {endpoint} "
            f"HTTP {response.status_code}"
        )

        if response.status_code == 200:

            return response.json()

        print(
            "❌ API:",
            response.text
        )

    except Exception as e:

        print(
            f"❌ Error API-Football: {e}"
        )

    return None

# ============================================================
# BUSCAR FIXTURE
# ============================================================

def buscar_fixture(apuesta):

    fecha = datetime.fromisoformat(
        apuesta["fecha"]
    )

    fecha_api = fecha.strftime(
        "%Y-%m-%d"
    )

    data = api_get(
        "/fixtures",
        {
            "date": fecha_api
        }
    )

    if not data:
        return None

    fixtures = data.get(
        "response",
        []
    )

    local = apuesta["local"].lower()
    visitante = apuesta["visitante"].lower()

    # --------------------------------------------------------
    # BÚSQUEDA FLEXIBLE
    # --------------------------------------------------------

    for fixture in fixtures:

        teams = fixture.get(
            "teams",
            {}
        )

        home = teams.get(
            "home",
            {}
        ).get(
            "name",
            ""
        ).lower()

        away = teams.get(
            "away",
            {}
        ).get(
            "name",
            ""
        ).lower()

        if (
            (local in home or home in local)
            and
            (visitante in away or away in visitante)
        ):

            return fixture

    return None

# ============================================================
# ACTUALIZAR RESULTADOS
# ============================================================

def actualizar_resultados():

    cambios = 0

    for apuesta in datos["apuestas"]:

        if apuesta["estado"] != "PENDIENTE":
            continue

        fixture = None

        # Si ya tenemos fixture ID
        if apuesta.get("fixture_id"):

            data = api_get(
                "/fixtures",
                {
                    "id": apuesta["fixture_id"]
                }
            )

            if data:

                lista = data.get(
                    "response",
                    []
                )

                if lista:
                    fixture = lista[0]

        # Si no tenemos ID, buscamos
        if not fixture:

            fixture = buscar_fixture(
                apuesta
            )

        if not fixture:
            continue

        apuesta["fixture_id"] = (
            fixture
            .get("fixture", {})
            .get("id")
        )

        resultado = evaluar_apuesta(
            apuesta,
            fixture
        )

        if resultado:

            apuesta["estado"] = (
                resultado["estado"]
            )

            apuesta["resultado"] = (
                resultado["marcador"]
            )

            apuesta["ganancia"] = (
                resultado["ganancia"]
            )

            cambios += 1

            emoji = (
                "🟢"
                if resultado["estado"] == "GANADA"
                else "🔴"
            )

            enviar(
                f"{emoji} <b>APUESTA FINALIZADA</b>\n\n"
                f"⚽ {escape(apuesta['local'])} "
                f"vs "
                f"{escape(apuesta['visitante'])}\n\n"
                f"🎯 {escape(apuesta['estrategia'])}\n"
                f"📊 Resultado: "
                f"<b>{resultado['marcador']}</b>\n\n"
                f"{emoji} <b>{resultado['estado']}</b>\n"
                f"💰 Resultado: "
                f"<b>${resultado['ganancia']:,.0f}</b>"
            )

    if cambios:
        guardar_datos(datos)

    return cambios

# ============================================================
# ESTADÍSTICAS
# ============================================================

def calcular_estadisticas(apuestas):

    finalizadas = [
        a for a in apuestas
        if a["estado"] in [
            "GANADA",
            "PERDIDA"
        ]
    ]

    ganadas = sum(
        1 for a in finalizadas
        if a["estado"] == "GANADA"
    )

    perdidas = sum(
        1 for a in finalizadas
        if a["estado"] == "PERDIDA"
    )

    apostado = sum(
        a["stake"]
        for a in finalizadas
    )

    ganancias = sum(
        a["ganancia"]
        for a in finalizadas
    )

    efectividad = (
        ganadas / len(finalizadas) * 100
        if finalizadas
        else 0
    )

    roi = (
        ganancias / apostado * 100
        if apostado
        else 0
    )

    return {
        "total": len(finalizadas),
        "ganadas": ganadas,
        "perdidas": perdidas,
        "apostado": apostado,
        "ganancias": ganancias,
        "efectividad": efectividad,
        "roi": roi
    }

# ============================================================
# FILTRAR PERIODOS
# ============================================================

def apuestas_periodo(periodo):

    hoy = fecha_colombia()

    resultado = []

    for apuesta in datos["apuestas"]:

        fecha = datetime.fromisoformat(
            apuesta["fecha"]
        ).date()

        if periodo == "hoy":

            if fecha == hoy:
                resultado.append(apuesta)

        elif periodo == "semana":

            inicio = hoy - timedelta(
                days=hoy.weekday()
            )

            if inicio <= fecha <= hoy:
                resultado.append(apuesta)

        elif periodo == "mes":

            if (
                fecha.year == hoy.year
                and fecha.month == hoy.month
            ):
                resultado.append(apuesta)

    return resultado

# ============================================================
# PANEL
# ============================================================

def panel(periodo="total"):

    if periodo == "total":

        apuestas = datos["apuestas"]

    else:

        apuestas = apuestas_periodo(
            periodo
        )

    stats = calcular_estadisticas(
        apuestas
    )

    pendientes = sum(
        1 for a in apuestas
        if a["estado"] == "PENDIENTE"
    )

    signo = (
        "🟢"
        if stats["ganancias"] >= 0
        else "🔴"
    )

    titulo = {
        "total": "💎 PANEL GENERAL",
        "hoy": "📅 ESTADÍSTICAS DE HOY",
        "semana": "📆 ESTADÍSTICAS DE LA SEMANA",
        "mes": "🗓 ESTADÍSTICAS DEL MES"
    }.get(
        periodo,
        "💎 PANEL"
    )

    mensaje = (
        f"<b>{titulo}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 Apuesta fija: "
        f"<b>${STAKE:,.0f}</b>\n\n"

        f"🎯 Apuestas: "
        f"<b>{stats['total']}</b>\n"

        f"🟢 Ganadas: "
        f"<b>{stats['ganadas']}</b>\n"

        f"🔴 Perdidas: "
        f"<b>{stats['perdidas']}</b>\n"

        f"⏳ Pendientes: "
        f"<b>{pendientes}</b>\n\n"

        f"📊 Efectividad: "
        f"<b>{stats['efectividad']:.2f}%</b>\n"

        f"📈 ROI: "
        f"<b>{stats['roi']:.2f}%</b>\n\n"

        f"{signo} Resultado neto: "
        f"<b>${stats['ganancias']:,.0f}</b>\n"
    )

    return mensaje

# ============================================================
# ESTRATEGIAS MÁS EFICIENTES
# ============================================================

def estrategias():

    grupos = {}

    for apuesta in datos["apuestas"]:

        if apuesta["estado"] not in [
            "GANADA",
            "PERDIDA"
        ]:
            continue

        nombre = apuesta["estrategia"]

        if nombre not in grupos:

            grupos[nombre] = {
                "total": 0,
                "ganadas": 0,
                "ganancia": 0
            }

        grupos[nombre]["total"] += 1

        if apuesta["estado"] == "GANADA":
            grupos[nombre]["ganadas"] += 1

        grupos[nombre]["ganancia"] += (
            apuesta["ganancia"]
        )

    ranking = []

    for nombre, info in grupos.items():

        efectividad = (
            info["ganadas"]
            / info["total"]
            * 100
        )

        ranking.append(
            (
                efectividad,
                nombre,
                info
            )
        )

    ranking.sort(
        reverse=True
    )

    mensaje = (
        "🏆 <b>ESTRATEGIAS MÁS EFICIENTES</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    if not ranking:

        mensaje += "Todavía no hay apuestas finalizadas."

        return mensaje

    for posicion, item in enumerate(
        ranking[:10],
        1
    ):

        efectividad, nombre, info = item

        emoji = (
            "🥇"
            if posicion == 1
            else
            "🥈"
            if posicion == 2
            else
            "🥉"
            if posicion == 3
            else
            "🎯"
        )

        mensaje += (
            f"{emoji} <b>{posicion}. "
            f"{escape(nombre)}</b>\n"
            f"   Apuestas: {info['total']}\n"
            f"   🟢 {info['ganadas']}\n"
            f"   📊 {efectividad:.1f}%\n"
            f"   💰 ${info['ganancia']:,.0f}\n\n"
        )

    return mensaje

# ============================================================
# APUESTAS PENDIENTES
# ============================================================

def pendientes():

    lista = [
        a for a in datos["apuestas"]
        if a["estado"] == "PENDIENTE"
    ]

    mensaje = (
        "🎯 <b>APUESTAS PENDIENTES</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    if not lista:

        mensaje += "No hay apuestas pendientes."

        return mensaje

    for apuesta in lista[-15:]:

        cuota = (
            f"{apuesta['cuota']:.2f}"
            if apuesta.get("cuota")
            else "N/D"
        )

        mensaje += (
            f"⚽ <b>{escape(apuesta['local'])}</b>\n"
            f"vs "
            f"<b>{escape(apuesta['visitante'])}</b>\n"
            f"🎯 {escape(apuesta['estrategia'])}\n"
            f"💵 Cuota: {cuota}\n"
            f"💰 ${STAKE:,.0f}\n\n"
        )

    return mensaje

# ============================================================
# PROCESAR MENSAJE RECIBIDO
# ============================================================

def procesar_mensaje(message):

    texto = message.get(
        "text",
        ""
    )

    if not texto:
        return

    chat_id = (
        message
        .get("chat", {})
        .get("id")
    )

    # --------------------------------------------------------
    # PANEL
    # --------------------------------------------------------

    if texto.startswith("/panel"):

        enviar(
            panel(),
            teclado_panel()
        )

        return

    if texto.startswith("/hoy"):

        enviar(
            panel("hoy"),
            teclado_panel()
        )

        return

    if texto.startswith("/semana"):

        enviar(
            panel("semana"),
            teclado_panel()
        )

        return

    if texto.startswith("/mes"):

        enviar(
            panel("mes"),
            teclado_panel()
        )

        return

    if texto.startswith("/estrategias"):

        enviar(
            estrategias(),
            teclado_panel()
        )

        return

    if texto.startswith("/pendientes"):

        enviar(
            pendientes(),
            teclado_panel()
        )

        return

    if texto.startswith("/start"):

        enviar(
            "🤖 <b>BETMINES TRACKER</b>\n\n"
            "Reenvíame cualquier alerta de BetMines "
            "y yo me encargo del resto.\n\n"
            "💰 Apuesta fija: <b>$5.000 COP</b>\n"
            "📊 Guardaré la estrategia.\n"
            "⚽ Esperaré el resultado final.\n"
            "🟢 Marcaré GANADA.\n"
            "🔴 Marcaré PERDIDA.\n\n"
            "Después puedes consultar todas "
            "las estadísticas desde el panel.",
            teclado_panel()
        )

        return

    # --------------------------------------------------------
    # ALERTA
    # --------------------------------------------------------

    apuesta, error = procesar_alerta(
        texto
    )

    if error:

        enviar(error)

        return

    # Evitar duplicados
    for existente in datos["apuestas"]:

        if (
            existente["local"] == apuesta["local"]
            and
            existente["visitante"] == apuesta["visitante"]
            and
            existente["fecha"] == apuesta["fecha"]
            and
            existente["estrategia"] == apuesta["estrategia"]
        ):

            enviar(
                "⚠️ <b>Esta apuesta ya está registrada.</b>"
            )

            return

    datos["apuestas"].append(
        apuesta
    )

    guardar_datos(datos)

    cuota = (
        f"{apuesta['cuota']:.2f}"
        if apuesta.get("cuota")
        else "No encontrada"
    )

    enviar(
        "✅ <b>APUESTA REGISTRADA</b>\n\n"
        f"⚽ <b>{escape(apuesta['local'])}</b>\n"
        f"vs "
        f"<b>{escape(apuesta['visitante'])}</b>\n\n"
        f"🏆 {escape(apuesta['liga'])}\n"
        f"🎯 {escape(apuesta['estrategia'])}\n"
        f"💵 Cuota: <b>{cuota}</b>\n"
        f"💰 Apuesta: <b>${STAKE:,.0f}</b>\n\n"
        "⏳ <b>Resultado: PENDIENTE</b>\n\n"
        "Cuando termine el partido consultaré "
        "el resultado final automáticamente.",
        teclado_panel()
    )

# ============================================================
# CALLBACKS
# ============================================================

def procesar_callback(callback):

    callback_id = callback.get(
        "id"
    )

    responder_callback(
        callback_id
    )

    data = callback.get(
        "data"
    )

    chat_id = (
        callback
        .get("message", {})
        .get("chat", {})
        .get("id")
    )

    message_id = (
        callback
        .get("message", {})
        .get("message_id")
    )

    if data == "panel":

        editar(
            chat_id,
            message_id,
            panel(),
            teclado_panel()
        )

    elif data == "hoy":

        editar(
            chat_id,
            message_id,
            panel("hoy"),
            teclado_panel()
        )

    elif data == "semana":

        editar(
            chat_id,
            message_id,
            panel("semana"),
            teclado_panel()
        )

    elif data == "mes":

        editar(
            chat_id,
            message_id,
            panel("mes"),
            teclado_panel()
        )

    elif data == "estrategias":

        editar(
            chat_id,
            message_id,
            estrategias(),
            teclado_panel()
        )

    elif data == "pendientes":

        editar(
            chat_id,
            message_id,
            pendientes(),
            teclado_panel()
        )

# ============================================================
# LEER TELEGRAM
# ============================================================

def obtener_updates():

    offset = datos.get(
        "ultimo_update_id",
        0
    ) + 1

    resultado = telegram(
        "getUpdates",
        {
            "offset": offset,
            "timeout": 5
        }
    )

    if not resultado:
        return []

    return resultado.get(
        "result",
        []
    )

# ============================================================
# PROCESAR UPDATES
# ============================================================

def procesar_updates():

    updates = obtener_updates()

    for update in updates:

        update_id = update.get(
            "update_id"
        )

        if update_id:

            datos["ultimo_update_id"] = update_id

        if "message" in update:

            procesar_mensaje(
                update["message"]
            )

        elif "callback_query" in update:

            procesar_callback(
                update["callback_query"]
            )

    if updates:

        guardar_datos(datos)

# ============================================================
# MAIN
# ============================================================

def main():

    print("")
    print("🚀 Iniciando BetMines Tracker...")
    print("")

    # Primero comprobar resultados
    print("🔎 Comprobando apuestas pendientes...")

    actualizadas = actualizar_resultados()

    print(
        f"📊 Apuestas actualizadas: "
        f"{actualizadas}"
    )

    # Luego leer Telegram
    print("📨 Revisando Telegram...")

    procesar_updates()

    print("")
    print("✅ Ejecución terminada.")

# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    main()