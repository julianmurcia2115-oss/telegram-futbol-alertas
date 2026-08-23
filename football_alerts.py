import os
import re
import json
import time
import requests
from datetime import datetime, timezone, timedelta

# ============================================================
# CONFIGURACIÓN
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

STAKE = 5000
DATA_FILE = "signals.json"
STATE_FILE = "bot_state.json"

API_URL = "https://v3.football.api-sports.io"

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
# SESIONES
# ============================================================

telegram = requests.Session()
api = requests.Session()

api.headers.update({
    "x-apisports-key": API_FOOTBALL_KEY
})


# ============================================================
# DATOS
# ============================================================

def cargar_apuestas():
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            datos = json.load(f)

        if isinstance(datos, list):
            return datos

    except Exception as e:
        print(f"❌ Error leyendo {DATA_FILE}: {e}")

    return []


def guardar_apuestas(apuestas):
    temporal = DATA_FILE + ".tmp"

    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(
            apuestas,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temporal, DATA_FILE)


def cargar_estado():
    if not os.path.exists(STATE_FILE):
        return {
            "last_update_id": 0
        }

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "last_update_id": 0
        }


def guardar_estado(estado):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            estado,
            f,
            ensure_ascii=False,
            indent=2
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
        response = telegram.post(
            url,
            data=data or {},
            timeout=40
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


def enviar_telegram(mensaje, botones=None):
    data = {
        "chat_id": CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    if botones:
        data["reply_markup"] = json.dumps(botones)

    return telegram_request(
        "sendMessage",
        data
    )


def editar_mensaje(
    chat_id,
    message_id,
    mensaje,
    botones=None
):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": mensaje,
        "parse_mode": "HTML"
    }

    if botones:
        data["reply_markup"] = json.dumps(botones)

    return telegram_request(
        "editMessageText",
        data
    )


def responder_callback(callback_id):
    telegram_request(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


# ============================================================
# PANEL
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


def calcular_estadisticas(apuestas):
    total = len(apuestas)

    ganadas = sum(
        1 for a in apuestas
        if a.get("status") == "GANADA"
    )

    perdidas = sum(
        1 for a in apuestas
        if a.get("status") == "PERDIDA"
    )

    pendientes = sum(
        1 for a in apuestas
        if a.get("status") == "PENDIENTE"
    )

    profit = sum(
        float(a.get("profit", 0))
        for a in apuestas
        if a.get("status") in [
            "GANADA",
            "PERDIDA"
        ]
    )

    resueltas = ganadas + perdidas

    efectividad = (
        ganadas / resueltas * 100
        if resueltas
        else 0
    )

    apostado = resueltas * STAKE

    roi = (
        profit / apostado * 100
        if apostado
        else 0
    )

    return {
        "total": total,
        "ganadas": ganadas,
        "perdidas": perdidas,
        "pendientes": pendientes,
        "profit": profit,
        "efectividad": efectividad,
        "roi": roi
    }


def formato_dinero(valor):
    return f"${valor:,.0f} COP"


def texto_panel(apuestas):
    e = calcular_estadisticas(apuestas)

    signo = "+" if e["profit"] > 0 else ""

    return (
        "📊 <b>PANEL FOOTBALL ALERTS</b>\n\n"
        f"💰 Capital por apuesta: "
        f"<b>{formato_dinero(STAKE)}</b>\n\n"
        f"🎯 Total apuestas: <b>{e['total']}</b>\n"
        f"🟢 Ganadas: <b>{e['ganadas']}</b>\n"
        f"🔴 Perdidas: <b>{e['perdidas']}</b>\n"
        f"🟡 Pendientes: <b>{e['pendientes']}</b>\n\n"
        f"💵 Ganancia/Pérdida: "
        f"<b>{signo}{formato_dinero(e['profit'])}</b>\n"
        f"📈 Efectividad: "
        f"<b>{e['efectividad']:.1f}%</b>\n"
        f"📊 ROI: <b>{e['roi']:.2f}%</b>"
    )


# ============================================================
# ESTRATEGIAS
# ============================================================

def estrategias(apuestas):
    datos = {}

    for a in apuestas:
        nombre = a.get(
            "strategy",
            "Otra estrategia"
        )

        if nombre not in datos:
            datos[nombre] = []

        datos[nombre].append(a)

    if not datos:
        return "🏆 <b>ESTRATEGIAS</b>\n\nSin apuestas."

    resultados = []

    for nombre, lista in datos.items():

        resueltas = [
            a for a in lista
            if a.get("status") in [
                "GANADA",
                "PERDIDA"
            ]
        ]

        ganadas = sum(
            1 for a in resueltas
            if a.get("status") == "GANADA"
        )

        profit = sum(
            float(a.get("profit", 0))
            for a in resueltas
        )

        efectividad = (
            ganadas / len(resueltas) * 100
            if resueltas
            else 0
        )

        apostado = len(resueltas) * STAKE

        roi = (
            profit / apostado * 100
            if apostado
            else 0
        )

        resultados.append({
            "nombre": nombre,
            "total": len(lista),
            "ganadas": ganadas,
            "efectividad": efectividad,
            "roi": roi,
            "profit": profit
        })

    resultados.sort(
        key=lambda x: x["roi"],
        reverse=True
    )

    mensaje = (
        "🏆 <b>ESTRATEGIAS MÁS EFICIENTES</b>\n\n"
    )

    for i, r in enumerate(resultados[:10], 1):

        mensaje += (
            f"<b>{i}. {r['nombre']}</b>\n"
            f"🎯 Apuestas: {r['total']}\n"
            f"🟢 Ganadas: {r['ganadas']}\n"
            f"📈 Efectividad: "
            f"{r['efectividad']:.1f}%\n"
            f"📊 ROI: {r['roi']:.2f}%\n"
            f"💰 {formato_dinero(r['profit'])}\n\n"
        )

    return mensaje


# ============================================================
# RECONOCER ESTRATEGIA
# ============================================================

def reconocer_estrategia(texto):
    t = texto.lower()

    if (
        "más de 3,5" in t
        or "mas de 3,5" in t
        or "más de 3.5" in t
        or "mas de 3.5" in t
        or "over 3.5" in t
    ):
        return {
            "nombre": "Más de 3.5 goles",
            "tipo": "over",
            "linea": 3.5
        }

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
            "linea": 2.5
        }

    if (
        "menos de 3,5" in t
        or "menos de 3.5" in t
        or "under 3.5" in t
    ):
        return {
            "nombre": "Menos de 3.5 goles",
            "tipo": "under",
            "linea": 3.5
        }

    if (
        "menos de 2,5" in t
        or "menos de 2.5" in t
        or "under 2.5" in t
    ):
        return {
            "nombre": "Menos de 2.5 goles",
            "tipo": "under",
            "linea": 2.5
        }

    if (
        "ambos equipos marcan" in t
        or "ambos marcan" in t
        or "btts" in t
    ):
        if re.search(r"\bno\b", t):
            return {
                "nombre": "BTTS - NO",
                "tipo": "btts_no"
            }

        return {
            "nombre": "BTTS - SÍ",
            "tipo": "btts_si"
        }

    if "empate" in t or "draw" in t:
        return {
            "nombre": "Empate",
            "tipo": "draw"
        }

    if (
        "local gana" in t
        or "ganador local" in t
    ):
        return {
            "nombre": "Victoria local",
            "tipo": "home"
        }

    if (
        "visitante gana" in t
        or "ganador visitante" in t
    ):
        return {
            "nombre": "Victoria visitante",
            "tipo": "away"
        }

    return {
        "nombre": "Otra estrategia",
        "tipo": "other"
    }


# ============================================================
# EXTRAER EQUIPOS
# ============================================================

def extraer_equipos(texto):

    patrones = [
        r"🆚\s*(.+?)\s*-\s*(.+?)(?:\n|$)",
        r"🆚\s*(.+?)\s+vs\s+(.+?)(?:\n|$)",
        r"(?:vs|VS|Vs)\s+(.+?)\s*-\s*(.+?)(?:\n|$)"
    ]

    for patron in patrones:

        m = re.search(
            patron,
            texto
        )

        if m:
            home = m.group(1).strip()
            away = m.group(2).strip()

            if home and away:
                return home, away

    return None, None


# ============================================================
# FECHA
# ============================================================

def extraer_fecha(texto):

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
        return datetime(
            int(m.group(3)),
            meses[m.group(2)],
            int(m.group(1)),
            int(m.group(4)),
            int(m.group(5)),
            tzinfo=timezone.utc
        ).isoformat()

    except Exception:
        return None


# ============================================================
# CUOTA
# ============================================================

def extraer_cuota(texto):

    patrones = [
        r"pinnacle\s*:\s*([0-9]+(?:[.,][0-9]+)?)",
        r"cuotas?.*?([0-9]+\.[0-9]+)"
    ]

    for patron in patrones:

        m = re.search(
            patron,
            texto.lower()
        )

        if m:
            try:
                return float(
                    m.group(1).replace(",", ".")
                )
            except Exception:
                pass

    return 0


# ============================================================
# CREAR APUESTA
# ============================================================

def crear_apuesta(texto):

    estrategia = reconocer_estrategia(texto)

    home, away = extraer_equipos(texto)

    fecha = extraer_fecha(texto)

    cuota = extraer_cuota(texto)

    ahora = datetime.now(timezone.utc)

    return {
        "id": str(
            int(time.time() * 1000)
        ),

        "created_at": ahora.isoformat(),

        "match_date": fecha,

        "home": home or "Desconocido",

        "away": away or "Desconocido",

        "strategy": estrategia["nombre"],

        "type": estrategia["tipo"],

        "line": estrategia.get("linea"),

        "stake": STAKE,

        "odds": cuota,

        "status": "PENDIENTE",

        "profit": 0,

        "result": None,

        "original_alert": texto
    }


# ============================================================
# NORMALIZAR EQUIPOS
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
# BUSCAR FIXTURE
# ============================================================

def buscar_fixture(home, away, fecha):

    if not fecha:
        return None

    try:
        fecha_dt = datetime.fromisoformat(fecha)
        fecha_api = fecha_dt.strftime("%Y-%m-%d")
    except Exception:
        return None

    try:

        response = api.get(
            f"{API_URL}/fixtures",
            params={
                "date": fecha_api
            },
            timeout=30
        )

        print(
            f"API-Football /fixtures HTTP "
            f"{response.status_code}"
        )

        if response.status_code != 200:
            return None

        fixtures = response.json().get(
            "response",
            []
        )

        hn_busqueda = normalizar(home)
        an_busqueda = normalizar(away)

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
                hn_busqueda in hn
                or hn in hn_busqueda
            ) and (
                an_busqueda in an
                or an in an_busqueda
            ):
                return fixture

    except Exception as e:
        print(f"❌ Error API: {e}")

    return None


# ============================================================
# DETERMINAR RESULTADO
# ============================================================

def determinar_resultado(apuesta, fixture):

    estado = fixture.get(
        "fixture",
        {}
    ).get(
        "status",
        {}
    ).get(
        "short"
    )

    if estado not in [
        "FT",
        "AET",
        "PEN"
    ]:
        return None

    goles = fixture.get(
        "goals",
        {}
    )

    hg = goles.get("home")
    ag = goles.get("away")

    if hg is None or ag is None:
        return None

    total = hg + ag

    tipo = apuesta.get("type")

    ganada = False

    if tipo == "over":
        ganada = total > float(
            apuesta.get("line")
        )

    elif tipo == "under":
        ganada = total < float(
            apuesta.get("line")
        )

    elif tipo == "btts_si":
        ganada = hg > 0 and ag > 0

    elif tipo == "btts_no":
        ganada = hg == 0 or ag == 0

    elif tipo == "draw":
        ganada = hg == ag

    elif tipo == "home":
        ganada = hg > ag

    elif tipo == "away":
        ganada = ag > hg

    else:
        return None

    if ganada:

        cuota = float(
            apuesta.get("odds") or 0
        )

        profit = (
            round(STAKE * (cuota - 1), 2)
            if cuota > 1
            else STAKE
        )

        return {
            "status": "GANADA",
            "profit": profit,
            "score": f"{hg}-{ag}"
        }

    return {
        "status": "PERDIDA",
        "profit": -STAKE,
        "score": f"{hg}-{ag}"
    }


# ============================================================
# ACTUALIZAR RESULTADOS
# ============================================================

def actualizar_resultados():

    apuestas = cargar_apuestas()

    cambios = False

    pendientes = [
        a for a in apuestas
        if a.get("status") == "PENDIENTE"
    ]

    print(
        f"🟡 Pendientes a revisar: "
        f"{len(pendientes)}"
    )

    for apuesta in pendientes:

        print(
            f"🔎 {apuesta.get('home')} "
            f"vs {apuesta.get('away')}"
        )

        fixture = buscar_fixture(
            apuesta.get("home"),
            apuesta.get("away"),
            apuesta.get("match_date")
        )

        if not fixture:
            print("ℹ️ Fixture todavía no encontrado.")
            continue

        resultado = determinar_resultado(
            apuesta,
            fixture
        )

        if not resultado:
            print("⏳ Partido todavía no finalizado.")
            continue

        apuesta["status"] = resultado["status"]
        apuesta["profit"] = resultado["profit"]
        apuesta["result"] = resultado["score"]
        apuesta["finished_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        cambios = True

        icono = (
            "🟢"
            if resultado["status"] == "GANADA"
            else "🔴"
        )

        enviar_telegram(
            f"{icono} <b>APUESTA FINALIZADA</b>\n\n"
            f"⚽ {apuesta['home']} vs "
            f"{apuesta['away']}\n"
            f"🎯 {apuesta['strategy']}\n"
            f"📊 Resultado: {resultado['score']}\n\n"
            f"<b>{resultado['status']}</b>\n"
            f"💰 {formato_dinero(resultado['profit'])}"
        )

    if cambios:
        guardar_apuestas(apuestas)

    return cambios


# ============================================================
# RECIBIR ALERTAS DE TELEGRAM
# ============================================================

def procesar_mensajes():

    estado = cargar_estado()

    offset = estado.get(
        "last_update_id",
        0
    ) + 1

    respuesta = telegram_request(
        "getUpdates",
        {
            "offset": offset,
            "timeout": 5,
            "allowed_updates": json.dumps(
                ["message", "callback_query"]
            )
        }
    )

    if not respuesta:
        return False

    actualizaciones = respuesta.get(
        "result",
        []
    )

    apuestas = cargar_apuestas()

    cambios = False

    for update in actualizaciones:

        update_id = update.get(
            "update_id",
            0
        )

        estado["last_update_id"] = update_id

        # ====================================================
        # MENSAJES
        # ====================================================

        mensaje = update.get("message")

        if mensaje:

            chat_id = str(
                mensaje.get(
                    "chat",
                    {}
                ).get(
                    "id"
                )
            )

            if chat_id != str(CHAT_ID):
                continue

            texto = mensaje.get(
                "text",
                ""
            )

            if not texto:
                continue

            if texto == "/start":

                enviar_telegram(
                    "⚽ <b>FOOTBALL ALERTS</b>\n\n"
                    "Bot conectado correctamente.\n\n"
                    "Envía tus alertas de BetMines "
                    "y las registraré automáticamente.",
                    teclado_panel()
                )

                continue

            if texto == "/panel":

                enviar_telegram(
                    texto_panel(apuestas),
                    teclado_panel()
                )

                continue

            if texto == "/estrategias":

                enviar_telegram(
                    estrategias(apuestas),
                    teclado_panel()
                )

                continue

            # ------------------------------------------------
            # RECONOCER ALERTA
            # ------------------------------------------------

            if (
                "🆚" in texto
                or "más de" in texto.lower()
                or "mas de" in texto.lower()
                or "menos de" in texto.lower()
                or "ambos equipos" in texto.lower()
                or "btts" in texto.lower()
            ):

                apuesta = crear_apuesta(texto)

                if (
                    apuesta["home"] == "Desconocido"
                    or apuesta["away"] == "Desconocido"
                ):
                    print(
                        "⚠️ No se pudieron reconocer "
                        "los equipos."
                    )
                    continue

                # Evitar duplicados
                duplicado = any(
                    a.get("original_alert") == texto
                    for a in apuestas
                )

                if not duplicado:

                    apuestas.append(apuesta)

                    cambios = True

                    enviar_telegram(
                        "📝 <b>APUESTA REGISTRADA</b>\n\n"
                        f"⚽ {apuesta['home']} vs "
                        f"{apuesta['away']}\n"
                        f"🎯 {apuesta['strategy']}\n"
                        f"💰 Capital: "
                        f"{formato_dinero(STAKE)}\n"
                        f"🟡 Estado: PENDIENTE"
                    )

        # ====================================================
        # BOTONES
        # ====================================================

        callback = update.get(
            "callback_query"
        )

        if callback:

            responder_callback(
                callback.get("id")
            )

            data = callback.get(
                "data"
            )

            mensaje = callback.get(
                "message",
                {}
            )

            chat_id = mensaje.get(
                "chat",
                {}
            ).get(
                "id"
            )

            message_id = mensaje.get(
                "message_id"
            )

            if str(chat_id) != str(CHAT_ID):
                continue

            if data == "panel":

                editar_mensaje(
                    chat_id,
                    message_id,
                    texto_panel(apuestas),
                    teclado_panel()
                )

            elif data == "estrategias":

                editar_mensaje(
                    chat_id,
                    message_id,
                    estrategias(apuestas),
                    teclado_panel()
                )

            elif data in [
                "hoy",
                "semana",
                "mes",
                "todas"
            ]:

                filtradas = filtrar_periodo(
                    apuestas,
                    data
                )

                editar_mensaje(
                    chat_id,
                    message_id,
                    texto_panel(filtradas),
                    teclado_panel()
                )

            elif data == "rendimiento":

                e = calcular_estadisticas(apuestas)

                mensaje_rendimiento = (
                    "💰 <b>RENDIMIENTO</b>\n\n"
                    f"💵 Ganancia/Pérdida: "
                    f"{formato_dinero(e['profit'])}\n"
                    f"📈 Efectividad: "
                    f"{e['efectividad']:.1f}%\n"
                    f"📊 ROI: "
                    f"{e['roi']:.2f}%"
                )

                editar_mensaje(
                    chat_id,
                    message_id,
                    mensaje_rendimiento,
                    teclado_panel()
                )

    guardar_estado(estado)

    if cambios:
        guardar_apuestas(apuestas)

    return cambios


# ============================================================
# FILTROS
# ============================================================

def fecha_apuesta(apuesta):

    valor = (
        apuesta.get("finished_at")
        or apuesta.get("created_at")
    )

    if not valor:
        return None

    try:
        return datetime.fromisoformat(
            valor.replace("Z", "+00:00")
        )
    except Exception:
        return None


def filtrar_periodo(apuestas, periodo):

    ahora = datetime.now(timezone.utc)

    if periodo == "todas":
        return apuestas

    if periodo == "hoy":

        inicio = datetime(
            ahora.year,
            ahora.month,
            ahora.day,
            tzinfo=timezone.utc
        )

    elif periodo == "semana":

        inicio = ahora - timedelta(
            days=7
        )

    elif periodo == "mes":

        inicio = datetime(
            ahora.year,
            ahora.month,
            1,
            tzinfo=timezone.utc
        )

    else:
        return apuestas

    resultado = []

    for apuesta in apuestas:

        fecha = fecha_apuesta(apuesta)

        if fecha and fecha >= inicio:
            resultado.append(apuesta)

    return resultado


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    print("")
    print("====================================")
    print("🚀 INICIANDO BETMINES TRACKER")
    print("====================================")

    apuestas = cargar_apuestas()

    print(
        f"📊 Apuestas existentes: "
        f"{len(apuestas)}"
    )

    # Primero procesa alertas nuevas
    procesar_mensajes()

    # Luego actualiza resultados finales
    actualizar_resultados()

    # Mostrar estado
    apuestas = cargar_apuestas()

    e = calcular_estadisticas(apuestas)

    print("")
    print("====================================")
    print("📊 ESTADÍSTICAS")
    print("====================================")
    print(f"🎯 Total: {e['total']}")
    print(f"🟢 Ganadas: {e['ganadas']}")
    print(f"🔴 Perdidas: {e['perdidas']}")
    print(f"🟡 Pendientes: {e['pendientes']}")
    print(
        f"💰 Ganancia/Pérdida: "
        f"{formato_dinero(e['profit'])}"
    )
    print(
        f"📈 Efectividad: "
        f"{e['efectividad']:.1f}%"
    )
    print(
        f"📊 ROI: "
        f"{e['roi']:.2f}%"
    )
    print("====================================")


if __name__ == "__main__":
    main()