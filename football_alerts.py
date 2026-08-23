import os
import re
import json
import time
import subprocess
import requests
from datetime import datetime, timedelta, timezone

# ============================================================
# CONFIGURACIÓN
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

STAKE = 5000
DATA_FILE = "signals.json"

API_URL = "https://v3.football.api-sports.io"

# Cuánto tiempo estará escuchando Telegram
POLL_SECONDS = 220

# ============================================================
# VALIDACIÓN
# ============================================================

print("====================================")
print("⚽ BETMINES TRACKER")
print("====================================")

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADO")
    raise SystemExit(1)

if not CHAT_ID:
    print("❌ TELEGRAM_CHAT_ID NO CONFIGURADO")
    raise SystemExit(1)

if not API_FOOTBALL_KEY:
    print("❌ API_FOOTBALL_KEY NO CONFIGURADA")
    raise SystemExit(1)

print("🤖 Telegram: CONFIGURADO")
print("💬 Chat ID: CONFIGURADO")
print("🔑 API-Football: CONFIGURADA")
print("💰 Apuesta fija: $5.000 COP")
print("====================================")


# ============================================================
# SESIÓN API FOOTBALL
# ============================================================

api_session = requests.Session()

api_session.headers.update({
    "x-apisports-key": API_FOOTBALL_KEY
})


# ============================================================
# ARCHIVO DE DATOS
# ============================================================

def cargar_datos():

    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)

            if isinstance(datos, list):
                return datos

    except Exception as e:
        print(f"⚠️ Error leyendo {DATA_FILE}: {e}")

    return []


def guardar_datos(datos):

    temporal = DATA_FILE + ".tmp"

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
        DATA_FILE
    )


# ============================================================
# PERSISTENCIA EN GITHUB
# ============================================================

def guardar_en_github():

    try:

        subprocess.run(
            ["git", "config", "user.name", "Football Alerts Bot"],
            check=False
        )

        subprocess.run(
            [
                "git",
                "config",
                "user.email",
                "football-alerts@users.noreply.github.com"
            ],
            check=False
        )

        subprocess.run(
            ["git", "add", DATA_FILE],
            check=False
        )

        resultado = subprocess.run(
            [
                "git",
                "diff",
                "--cached",
                "--quiet"
            ],
            capture_output=True
        )

        # 0 = no hay cambios
        if resultado.returncode == 0:
            return

        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "Actualizar estadísticas Football Alerts"
            ],
            check=False
        )

        branch = os.getenv(
            "GITHUB_REF_NAME",
            "main"
        )

        push = subprocess.run(
            [
                "git",
                "push",
                "origin",
                f"HEAD:{branch}"
            ],
            capture_output=True,
            text=True
        )

        if push.returncode == 0:
            print("💾 Datos guardados permanentemente en GitHub")
        else:
            print(
                "⚠️ No se pudo hacer push:",
                push.stderr
            )

    except Exception as e:

        print(
            f"⚠️ Error guardando en GitHub: {e}"
        )


# ============================================================
# TELEGRAM
# ============================================================

def telegram_request(method, data=None):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/{method}"
    )

    try:

        response = requests.post(
            url,
            data=data,
            timeout=40
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


def enviar_telegram(
    mensaje,
    reply_markup=None,
    chat_id=None
):

    destino = chat_id or CHAT_ID

    data = {
        "chat_id": destino,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(
            reply_markup
        )

    return telegram_request(
        "sendMessage",
        data
    )


def editar_mensaje(
    chat_id,
    message_id,
    mensaje,
    reply_markup=None
):

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(
            reply_markup
        )

    return telegram_request(
        "editMessageText",
        data
    )


def responder_callback(
    callback_id
):

    telegram_request(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


# ============================================================
# BOTONES
# ============================================================

def teclado_panel():

    return {
        "inline_keyboard": [

            [
                {
                    "text": "📅 Hoy",
                    "callback_data": "hoy"
                },
                {
                    "text": "📆 Semana",
                    "callback_data": "semana"
                }
            ],

            [
                {
                    "text": "🗓 Mes",
                    "callback_data": "mes"
                },
                {
                    "text": "📊 Todas",
                    "callback_data": "todas"
                }
            ],

            [
                {
                    "text": "🏆 Estrategias",
                    "callback_data": "estrategias"
                }
            ],

            [
                {
                    "text": "💰 Rendimiento",
                    "callback_data": "rendimiento"
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
# RECONOCER ESTRATEGIA
# ============================================================

def reconocer_estrategia(texto):

    texto_original = texto

    t = texto.lower()

    # Más de 3.5
    if (
        "más de 3,5" in t
        or "mas de 3,5" in t
        or "más de 3.5" in t
        or "mas de 3.5" in t
        or "over 3.5" in t
        or "over3.5" in t
    ):

        return {
            "nombre": "Más de 3.5 goles",
            "tipo": "over",
            "linea": 3.5,
            "objetivo": 4
        }

    # Más de 2.5
    if (
        "más de 2,5" in t
        or "mas de 2,5" in t
        or "más de 2.5" in t
        or "mas de 2.5" in t
        or "over 2.5" in t
    ):

        return {
            "nombre": "Más de 2.5 goles",
            "tipo": "over",
            "linea": 2.5,
            "objetivo": 3
        }

    # Menos de 3.5
    if (
        "menos de 3,5" in t
        or "menos de 3.5" in t
        or "under 3.5" in t
    ):

        return {
            "nombre": "Menos de 3.5 goles",
            "tipo": "under",
            "linea": 3.5,
            "objetivo": 3
        }

    # Menos de 2.5
    if (
        "menos de 2,5" in t
        or "menos de 2.5" in t
        or "under 2.5" in t
    ):

        return {
            "nombre": "Menos de 2.5 goles",
            "tipo": "under",
            "linea": 2.5,
            "objetivo": 2
        }

    # Ambos marcan
    if (
        "ambos equipos marcan" in t
        or "ambos marcan" in t
        or "btts" in t
    ):

        if (
            re.search(
                r"\bno\b",
                t
            )
            and (
                "ambos" in t
                or "btts" in t
            )
        ):

            return {
                "nombre": "BTTS - NO",
                "tipo": "btts_no"
            }

        return {
            "nombre": "BTTS - SÍ",
            "tipo": "btts_si"
        }

    # Empate
    if (
        "empate" in t
        or "draw" in t
    ):

        return {
            "nombre": "Empate",
            "tipo": "draw"
        }

    # Victoria local
    if (
        "ganador local" in t
        or "local gana" in t
        or "1x2 - 1" in t
    ):

        return {
            "nombre": "Victoria local",
            "tipo": "home"
        }

    # Victoria visitante
    if (
        "ganador visitante" in t
        or "visitante gana" in t
        or "1x2 - 2" in t
    ):

        return {
            "nombre": "Victoria visitante",
            "tipo": "away"
        }

    # Si no reconoce
    return {
        "nombre": "Otra estrategia",
        "tipo": "other"
    }


# ============================================================
# EXTRAER EQUIPOS
# ============================================================

def extraer_equipos(texto):

    # Busca:
    # 🆚 Ventura County - Portland Timbers II

    patrones = [

        r"🆚\s*(.+?)\s*-\s*(.+?)(?:\n|$)",

        r"(?:vs|VS|Vs)\s+(.+?)\s*-\s*(.+?)(?:\n|$)",

        r"(?:🆚)\s*(.+?)\s+(?:vs|VS|Vs)\s+(.+?)(?:\n|$)"

    ]

    for patron in patrones:

        encontrado = re.search(
            patron,
            texto
        )

        if encontrado:

            home = encontrado.group(1).strip()
            away = encontrado.group(2).strip()

            if home and away:

                return home, away

    return None, None


# ============================================================
# EXTRAER FECHA
# ============================================================

def extraer_fecha(texto):

    # Busca formatos como:
    # 24 ago 2026 02:00

    meses = {
        "ene": 1,
        "feb": 2,
        "mar": 3,
        "abr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dic": 12
    }

    patron = (
        r"(\d{1,2})\s+"
        r"(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)"
        r"\s+(\d{4})\s+"
        r"(\d{1,2}):(\d{2})"
    )

    m = re.search(
        patron,
        texto.lower()
    )

    if not m:
        return None

    try:

        dia = int(m.group(1))
        mes = meses[m.group(2)]
        año = int(m.group(3))
        hora = int(m.group(4))
        minuto = int(m.group(5))

        return datetime(
            año,
            mes,
            dia,
            hora,
            minuto,
            tzinfo=timezone.utc
        ).isoformat()

    except Exception:

        return None


# ============================================================
# EXTRAER CUOTA
# ============================================================

def extraer_cuota(texto):

    # Busca pinnacle: 2.27

    patrones = [

        r"pinnacle\s*:\s*([0-9]+(?:[.,][0-9]+)?)",

        r"cuota\s*:\s*([0-9]+(?:[.,][0-9]+)?)"

    ]

    for patron in patrones:

        m = re.search(
            patron,
            texto.lower()
        )

        if m:

            try:

                return float(
                    m.group(1).replace(
                        ",",
                        "."
                    )
                )

            except Exception:
                pass

    return 0


# ============================================================
# CREAR APUESTA
# ============================================================

def crear_apuesta(texto):

    estrategia = reconocer_estrategia(
        texto
    )

    home, away = extraer_equipos(
        texto
    )

    fecha = extraer_fecha(
        texto
    )

    cuota = extraer_cuota(
        texto
    )

    ahora = datetime.now(
        timezone.utc
    )

    apuesta = {

        "id": str(
            int(
                time.time() * 1000
            )
        ),

        "created_at": ahora.isoformat(),

        "match_date": fecha,

        "home": home or "Desconocido",

        "away": away or "Desconocido",

        "strategy": estrategia["nombre"],

        "type": estrategia["tipo"],

        "line": estrategia.get(
            "linea"
        ),

        "stake": STAKE,

        "odds": cuota,

        "status": "PENDIENTE",

        "profit": 0,

        "result": None,

        "original_alert": texto

    }

    return apuesta


# ============================================================
# ENCONTRAR PARTIDO EN API FOOTBALL
# ============================================================

def buscar_fixture(
    home,
    away,
    fecha
):

    if not fecha:
        return None

    try:

        fecha_dt = datetime.fromisoformat(
            fecha
        )

        fecha_api = fecha_dt.strftime(
            "%Y-%m-%d"
        )

    except Exception:

        fecha_api = datetime.now(
            timezone.utc
        ).strftime(
            "%Y-%m-%d"
        )

    try:

        response = api_session.get(
            f"{API_URL}/fixtures",
            params={
                "date": fecha_api
            },
            timeout=30
        )

        print(
            "API-Football:",
            response.status_code
        )

        if response.status_code != 200:
            return None

        data = response.json()

        fixtures = data.get(
            "response",
            []
        )

        home_busqueda = normalizar(
            home
        )

        away_busqueda = normalizar(
            away
        )

        mejor = None

        for fixture in fixtures:

            equipos = fixture.get(
                "teams",
                {}
            )

            h = equipos.get(
                "home",
                {}
            ).get(
                "name",
                ""
            )

            a = equipos.get(
                "away",
                {}
            ).get(
                "name",
                ""
            )

            hn = normalizar(h)
            an = normalizar(a)

            if (
                home_busqueda in hn
                or hn in home_busqueda
            ) and (
                away_busqueda in an
                or an in away_busqueda
            ):

                mejor = fixture
                break

        return mejor

    except Exception as e:

        print(
            f"❌ Error buscando fixture: {e}"
        )

        return None


# ============================================================
# NORMALIZAR
# ============================================================

def normalizar(texto):

    if not texto:
        return ""

    texto = texto.lower()

    texto = re.sub(
        r"[^a-z0-9áéíóúüñ ]",
        " ",
        texto
    )

    reemplazos = {

        " fc ": " ",
        " cf ": " ",
        " sc ": " ",
        " afc ": " ",
        " united ": " ",
        " utd ": " ",
        " club ": " "

    }

    texto = f" {texto} "

    for viejo, nuevo in reemplazos.items():

        texto = texto.replace(
            viejo,
            nuevo
        )

    return " ".join(
        texto.split()
    )


# ============================================================
# DETERMINAR RESULTADO
# ============================================================

def determinar_resultado(
    apuesta,
    fixture
):

    if not fixture:
        return None

    status = fixture.get(
        "fixture",
        {}
    ).get(
        "status",
        {}
    ).get(
        "short"
    )

    if status not in [
        "FT",
        "AET",
        "PEN"
    ]:

        return None

    goles = fixture.get(
        "goals",
        {}
    )

    home_goals = goles.get(
        "home"
    )

    away_goals = goles.get(
        "away"
    )

    if (
        home_goals is None
        or away_goals is None
    ):

        return None

    total = (
        home_goals +
        away_goals
    )

    tipo = apuesta["type"]

    ganada = False

    # --------------------------------------------------------
    # OVER
    # --------------------------------------------------------

    if tipo == "over":

        linea = apuesta.get(
            "line"
        )

        if linea is not None:
            ganada = total > linea

    # --------------------------------------------------------
    # UNDER
    # --------------------------------------------------------

    elif tipo == "under":

        linea = apuesta.get(
            "line"
        )

        if linea is not None:
            ganada = total < linea

    # --------------------------------------------------------
    # BTTS
    # --------------------------------------------------------

    elif tipo == "btts_si":

        ganada = (
            home_goals > 0
            and away_goals > 0
        )

    elif tipo == "btts_no":

        ganada = (
            home_goals == 0
            or away_goals == 0
        )

    # --------------------------------------------------------
    # EMPATE
    # --------------------------------------------------------

    elif tipo == "draw":

        ganada = (
            home_goals == away_goals
        )

    # --------------------------------------------------------
    # LOCAL
    # --------------------------------------------------------

    elif tipo == "home":

        ganada = (
            home_goals > away_goals
        )

    # --------------------------------------------------------
    # VISITANTE
    # --------------------------------------------------------

    elif tipo == "away":

        ganada = (
            away_goals > home_goals
        )

    else:

        return None

    if ganada:

        cuota = apuesta.get(
            "odds",
            0
        )

        if cuota and cuota > 1:

            profit = round(
                STAKE * (cuota - 1),
                2
            )

        else:

            profit = STAKE

        return {
            "status": "GANADA",
            "profit": profit,
            "score": f"{home_goals}-{away_goals}"
        }

    return {
        "status": "PERDIDA",
        "profit": -STAKE,
        "score": f"{home_goals}-{away_goals}"
    }


# ============================================================
# ACTUALIZAR APUESTAS PENDIENTES
# ============================================================

def actualizar_resultados():

    datos = cargar_datos()

    cambios = False

    for apuesta in datos:

        if apuesta.get(
            "status"
        ) != "PENDIENTE":

            continue

        print(
            f"🔎 Revisando: "
            f"{apuesta['home']} - "
            f"{apuesta['away']}"
        )

        fixture = buscar_fixture(
            apuesta["home"],
            apuesta["away"],
            apuesta.get("match_date")
        )

        if not fixture:

            continue

        resultado = determinar_resultado(
            apuesta,
            fixture
        )

        if not resultado:

            continue

        apuesta["status"] = resultado[
            "status"
        ]

        apuesta["profit"] = resultado[
            "profit"
        ]

        apuesta["result"] = resultado[
            "score"
        ]

        apuesta["finished_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        cambios = True

        icono = (
            "🟢"
            if apuesta["status"] == "GANADA"
            else "🔴"
        )

        enviar_telegram(

            f"{icono} <b>APUESTA FINALIZADA</b>\n\n"
            f"⚽ {apuesta['home']} vs "
            f"{apuesta['away']}\n"
            f"🎯 {apuesta['strategy']}\n"
            f"📊 Resultado: "
            f"{apuesta['result']}\n\n"
            f"<b>{apuesta['status']}</b>\n"
            f"💰 Resultado: "
            f"${apuesta['profit']:,.0f} COP"
        )

    if cambios:

        guardar_datos(
            datos
        )

        guardar_en_github()


# ============================================================
# FILTROS DE FECHA
# ============================================================

def inicio_hoy():

    ahora = datetime.now(
        timezone.utc
    )

    return datetime(
        ahora.year,
        ahora.month,
        ahora.day,
        tzinfo=timezone.utc
    )


def filtrar(datos, periodo):

    ahora = datetime.now(
        timezone.utc
    )

    if periodo == "hoy":

        inicio = inicio_hoy()

    elif periodo == "semana":

        inicio = (
            inicio_hoy()
            - timedelta(
                days=ahora.weekday()
            )
        )

    elif periodo == "mes":

        inicio = datetime(
            ahora.year,
            ahora.month,
            1,
            tzinfo=timezone.utc
        )

    else:

        return datos

    resultado = []

    for apuesta in datos:

        try:

            fecha = datetime.fromisoformat(
                apuesta["created_at"]
            )

            if fecha >= inicio:

                resultado.append(
                    apuesta
                )

        except Exception:
            pass

    return resultado


# ============================================================
# ESTADÍSTICAS
# ============================================================

def estadisticas(datos):

    ganadas = sum(
        1
        for x in datos
        if x.get("status") == "GANADA"
    )

    perdidas = sum(
        1
        for x in datos
        if x.get("status") == "PERDIDA"
    )

    pendientes = sum(
        1
        for x in datos
        if x.get("status") == "PENDIENTE"
    )

    apostado = (
        (ganadas + perdidas)
        * STAKE
    )

    ganancias = sum(
        x.get("profit", 0)
        for x in datos
        if x.get("status") != "PENDIENTE"
    )

    total_apuestas = (
        ganadas + perdidas
    )

    if total_apuestas > 0:

        efectividad = (
            ganadas /
            total_apuestas
        ) * 100

    else:

        efectividad = 0

    if apostado > 0:

        roi = (
            ganancias /
            apostado
        ) * 100

    else:

        roi = 0

    return {
        "ganadas": ganadas,
        "perdidas": perdidas,
        "pendientes": pendientes,
        "apostado": apostado,
        "ganancias": ganancias,
        "efectividad": efectividad,
        "roi": roi
    }


# ============================================================
# PANEL
# ============================================================

def construir_panel():

    datos = cargar_datos()

    s = estadisticas(
        datos
    )

    resultado = (
        "📊 <b>PANEL FOOTBALL ALERTS</b>\n\n"

        f"💰 Capital por apuesta: "
        f"<b>$5.000 COP</b>\n\n"

        f"🎯 Total apuestas: "
        f"<b>{len(datos)}</b>\n"

        f"🟢 Ganadas: "
        f"<b>{s['ganadas']}</b>\n"

        f"🔴 Perdidas: "
        f"<b>{s['perdidas']}</b>\n"

        f"🟡 Pendientes: "
        f"<b>{s['pendientes']}</b>\n\n"

        f"💵 Ganancia/Pérdida: "
        f"<b>${s['ganancias']:,.0f} COP</b>\n"

        f"📈 Efectividad: "
        f"<b>{s['efectividad']:.1f}%</b>\n"

        f"📊 ROI: "
        f"<b>{s['roi']:.2f}%</b>"
    )

    return resultado


# ============================================================
# PANEL POR PERIODO
# ============================================================

def panel_periodo(periodo):

    datos = cargar_datos()

    filtrados = filtrar(
        datos,
        periodo
    )

    s = estadisticas(
        filtrados
    )

    nombres = {
        "hoy": "📅 HOY",
        "semana": "📆 ESTA SEMANA",
        "mes": "🗓 ESTE MES",
        "todas": "📊 TODAS"
    }

    titulo = nombres.get(
        periodo,
        "📊 TODAS"
    )

    return (

        f"<b>{titulo}</b>\n\n"

        f"🎯 Apuestas: "
        f"{len(filtrados)}\n"

        f"🟢 Ganadas: "
        f"{s['ganadas']}\n"

        f"🔴 Perdidas: "
        f"{s['perdidas']}\n"

        f"🟡 Pendientes: "
        f"{s['pendientes']}\n\n"

        f"💰 Resultado: "
        f"<b>${s['ganancias']:,.0f} COP</b>\n"

        f"📈 Efectividad: "
        f"{s['efectividad']:.1f}%\n"

        f"📊 ROI: "
        f"{s['roi']:.2f}%"
    )


# ============================================================
# ESTRATEGIAS MÁS EFICIENTES
# ============================================================

def panel_estrategias():

    datos = cargar_datos()

    estrategias = {}

    for apuesta in datos:

        nombre = apuesta.get(
            "strategy",
            "Otra estrategia"
        )

        if nombre not in estrategias:

            estrategias[nombre] = {
                "total": 0,
                "ganadas": 0,
                "perdidas": 0,
                "profit": 0
            }

        if apuesta.get(
            "status"
        ) == "PENDIENTE":

            continue

        estrategias[nombre]["total"] += 1

        if apuesta.get(
            "status"
        ) == "GANADA":

            estrategias[nombre]["ganadas"] += 1

        elif apuesta.get(
            "status"
        ) == "PERDIDA":

            estrategias[nombre]["perdidas"] += 1

        estrategias[nombre]["profit"] += (
            apuesta.get(
                "profit",
                0
            )
        )

    ordenadas = sorted(
        estrategias.items(),
        key=lambda x: (
            (
                x[1]["ganadas"] /
                x[1]["total"]
            )
            if x[1]["total"]
            else 0
        ),
        reverse=True
    )

    mensaje = (
        "🏆 <b>ESTRATEGIAS MÁS EFICIENTES</b>\n\n"
    )

    if not ordenadas:

        return (
            mensaje +
            "Todavía no hay apuestas finalizadas."
        )

    for i, (
        nombre,
        datos_estrategia
    ) in enumerate(
        ordenadas[:10],
        1
    ):

        total = datos_estrategia[
            "total"
        ]

        ganadas = datos_estrategia[
            "ganadas"
        ]

        efectividad = (
            ganadas /
            total
        ) * 100 if total else 0

        profit = datos_estrategia[
            "profit"
        ]

        mensaje += (
            f"<b>{i}. {nombre}</b>\n"
            f"🟢 {ganadas} | "
            f"🔴 {datos_estrategia['perdidas']}\n"
            f"📈 {efectividad:.1f}%\n"
            f"💰 ${profit:,.0f} COP\n\n"
        )

    return mensaje


# ============================================================
# RENDIMIENTO
# ============================================================

def panel_rendimiento():

    datos = cargar_datos()

    hoy = estadisticas(
        filtrar(datos, "hoy")
    )

    semana = estadisticas(
        filtrar(datos, "semana")
    )

    mes = estadisticas(
        filtrar(datos, "mes")
    )

    return (

        "💰 <b>RENDIMIENTO</b>\n\n"

        "📅 <b>HOY</b>\n"
        f"Resultado: ${hoy['ganancias']:,.0f}\n"
        f"ROI: {hoy['roi']:.2f}%\n\n"

        "📆 <b>SEMANA</b>\n"
        f"Resultado: ${semana['ganancias']:,.0f}\n"
        f"ROI: {semana['roi']:.2f}%\n\n"

        "🗓 <b>MES</b>\n"
        f"Resultado: ${mes['ganancias']:,.0f}\n"
        f"ROI: {mes['roi']:.2f}%"
    )


# ============================================================
# PROCESAR ALERTA
# ============================================================

def procesar_alerta(texto):

    # Evitar comandos
    if texto.startswith("/"):
        return

    datos = cargar_datos()

    apuesta = crear_apuesta(
        texto
    )

    # Evitar duplicados
    for existente in datos:

        if (
            existente.get("home")
            == apuesta.get("home")
            and existente.get("away")
            == apuesta.get("away")
            and existente.get("strategy")
            == apuesta.get("strategy")
            and existente.get("match_date")
            == apuesta.get("match_date")
        ):

            enviar_telegram(
                "⚠️ Esta alerta ya está registrada."
            )

            return

    datos.append(
        apuesta
    )

    guardar_datos(
        datos
    )

    guardar_en_github()

    cuota = apuesta.get(
        "odds"
    )

    cuota_texto = (
        f"{cuota:.2f}"
        if cuota
        else "No encontrada"
    )

    mensaje = (

        "✅ <b>APUESTA REGISTRADA</b>\n\n"

        f"⚽ {apuesta['home']} vs "
        f"{apuesta['away']}\n\n"

        f"🎯 Estrategia: "
        f"<b>{apuesta['strategy']}</b>\n"

        f"💰 Apuesta: "
        f"<b>$5.000 COP</b>\n"

        f"🟢 Cuota: "
        f"<b>{cuota_texto}</b>\n\n"

        "🟡 Estado: <b>PENDIENTE</b>\n\n"

        "El bot comprobará el resultado "
        "cuando termine el partido."
    )

    enviar_telegram(
        mensaje
    )


# ============================================================
# PROCESAR MENSAJES
# ============================================================

def procesar_update(update):

    # --------------------------------------------------------
    # MENSAJE
    # --------------------------------------------------------

    message = update.get(
        "message"
    )

    if message:

        chat_id = str(
            message.get(
                "chat",
                {}
            ).get(
                "id"
            )
        )

        texto = message.get(
            "text",
            ""
        )

        if chat_id != str(CHAT_ID):

            return

        if texto == "/start":

            enviar_telegram(
                "🤖 <b>BETMINES TRACKER</b>\n\n"
                "Envíame directamente las alertas "
                "de BetMines y yo las registraré.\n\n"
                "💰 Apuesta fija: $5.000 COP\n"
                "🟢 Luego marcaré GANADA\n"
                "🔴 o PERDIDA\n\n"
                "Usa /panel para ver las estadísticas.",
                teclado_panel()
            )

            return

        if texto == "/panel":

            enviar_telegram(
                construir_panel(),
                teclado_panel()
            )

            return

        # Cualquier otro texto
        # se intenta interpretar como alerta
        if (
            "🆚" in texto
            or "🎯" in texto
            or "betmines" in texto.lower()
            or "pinnacle" in texto.lower()
        ):

            procesar_alerta(
                texto
            )

            return

    # --------------------------------------------------------
    # BOTÓN
    # --------------------------------------------------------

    callback = update.get(
        "callback_query"
    )

    if callback:

        responder_callback(
            callback.get(
                "id"
            )
        )

        callback_data = callback.get(
            "data"
        )

        message = callback.get(
            "message",
            {}
        )

        chat_id = str(
            message.get(
                "chat",
                {}
            ).get(
                "id"
            )
        )

        message_id = message.get(
            "message_id"
        )

        if chat_id != str(CHAT_ID):

            return

        if callback_data == "panel":

            editar_mensaje(
                chat_id,
                message_id,
                construir_panel(),
                teclado_panel()
            )

        elif callback_data in [
            "hoy",
            "semana",
            "mes",
            "todas"
        ]:

            editar_mensaje(
                chat_id,
                message_id,
                panel_periodo(
                    callback_data
                ),
                teclado_panel()
            )

        elif callback_data == "estrategias":

            editar_mensaje(
                chat_id,
                message_id,
                panel_estrategias(),
                teclado_panel()
            )

        elif callback_data == "rendimiento":

            editar_mensaje(
                chat_id,
                message_id,
                panel_rendimiento(),
                teclado_panel()
            )


# ============================================================
# TELEGRAM GET UPDATES
# ============================================================

def obtener_updates(offset=None):

    data = {
        "timeout": 25
    }

    if offset is not None:

        data["offset"] = offset

    return telegram_request(
        "getUpdates",
        data
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("")
    print("====================================")
    print("🚀 INICIANDO BETMINES TRACKER")
    print("====================================")

    # Primero revisar resultados
    actualizar_resultados()

    # --------------------------------------------------------
    # ESCUCHAR TELEGRAM
    # --------------------------------------------------------

    inicio = time.time()

    offset = None

    while (
        time.time() - inicio
        < POLL_SECONDS
    ):

        respuesta = obtener_updates(
            offset
        )

        if not respuesta:

            time.sleep(2)
            continue

        updates = respuesta.get(
            "result",
            []
        )

        for update in updates:

            update_id = update.get(
                "update_id"
            )

            if update_id is not None:

                offset = (
                    update_id + 1
                )

            try:

                procesar_update(
                    update
                )

            except Exception as e:

                print(
                    f"❌ Error procesando "
                    f"update: {e}"
                )

    # Volver a comprobar por si
    # llegó una actualización
    actualizar_resultados()

    print("")
    print("====================================")
    print("✅ EJECUCIÓN TERMINADA")
    print("====================================")


# ============================================================
# ARRANQUE
# ============================================================

if __name__ == "__main__":
    main()