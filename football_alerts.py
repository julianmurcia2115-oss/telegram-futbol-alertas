import os
import re
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ============================================================
# CONFIGURACIÓN
# ============================================================

API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BASE_URL = "https://v3.football.api-sports.io"

APUESTA = 5000

DATA_FILE = Path("apuestas.json")

# ============================================================
# VALIDACIÓN
# ============================================================

if not API_FOOTBALL_KEY:
    print("❌ API_FOOTBALL_KEY NO CONFIGURADA")
    raise SystemExit(1)

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADO")
    raise SystemExit(1)

if not CHAT_ID:
    print("❌ TELEGRAM_CHAT_ID NO CONFIGURADO")
    raise SystemExit(1)

print("====================================")
print("⚽ FOOTBALL ALERTS")
print("====================================")
print("🔑 API-Football: CONFIGURADA")
print("🤖 Telegram: CONFIGURADO")
print("💬 Chat ID: CONFIGURADO")
print(f"💰 Apuesta fija: ${APUESTA:,}")
print("====================================")


# ============================================================
# SESIÓN API-FOOTBALL
# ============================================================

session = requests.Session()

session.headers.update({
    "x-apisports-key": API_FOOTBALL_KEY,
    "Accept": "application/json"
})


# ============================================================
# BASE DE DATOS SIMPLE
# ============================================================

def cargar_apuestas():

    if not DATA_FILE.exists():
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return []


def guardar_apuestas(apuestas):

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            apuestas,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# TELEGRAM
# ============================================================

def telegram(method, data=None):

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

        if response.status_code != 200:
            print(
                "❌ Telegram:",
                response.status_code,
                response.text
            )
            return None

        return response.json()

    except Exception as e:

        print("❌ Error Telegram:", e)

        return None


def enviar_telegram(texto, reply_markup=None):

    data = {
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": "HTML"
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(
            reply_markup
        )

    return telegram(
        "sendMessage",
        data
    )


def editar_mensaje(
    chat_id,
    message_id,
    texto,
    reply_markup=None
):

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": texto,
        "parse_mode": "HTML"
    }

    if reply_markup:
        data["reply_markup"] = json.dumps(
            reply_markup
        )

    return telegram(
        "editMessageText",
        data
    )


# ============================================================
# BOTONES DEL PANEL
# ============================================================

def botones_panel():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "📊 Hoy",
                    "callback_data": "hoy"
                },
                {
                    "text": "📆 Semana",
                    "callback_data": "semana"
                }
            ],
            [
                {
                    "text": "🗓️ Mes",
                    "callback_data": "mes"
                },
                {
                    "text": "🎯 Apuestas",
                    "callback_data": "apuestas"
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
# FECHAS
# ============================================================

def fecha_local():

    return datetime.now(
        timezone(timedelta(hours=-5))
    )


# ============================================================
# ESTADÍSTICAS
# ============================================================

def calcular_estadisticas(apuestas):

    ahora = fecha_local()

    inicio_hoy = ahora.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    inicio_semana = inicio_hoy - timedelta(
        days=ahora.weekday()
    )

    inicio_mes = ahora.replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    def analizar(desde):

        seleccionadas = []

        for apuesta in apuestas:

            fecha = apuesta.get(
                "fecha",
                ""
            )

            try:
                fecha_dt = datetime.fromisoformat(
                    fecha
                )
            except Exception:
                continue

            if fecha_dt >= desde:
                seleccionadas.append(
                    apuesta
                )

        ganadas = sum(
            1 for x in seleccionadas
            if x.get("resultado") == "GANADA"
        )

        perdidas = sum(
            1 for x in seleccionadas
            if x.get("resultado") == "PERDIDA"
        )

        pendientes = sum(
            1 for x in seleccionadas
            if x.get("resultado") == "PENDIENTE"
        )

        total = len(seleccionadas)

        invertido = total * APUESTA

        ganancias = 0

        for apuesta in seleccionadas:

            if apuesta.get("resultado") == "GANADA":

                cuota = apuesta.get(
                    "cuota",
                    1.0
                )

                ganancias += (
                    APUESTA *
                    (cuota - 1)
                )

            elif apuesta.get("resultado") == "PERDIDA":

                ganancias -= APUESTA

        return {
            "total": total,
            "ganadas": ganadas,
            "perdidas": perdidas,
            "pendientes": pendientes,
            "invertido": invertido,
            "ganancias": ganancias
        }

    return {
        "hoy": analizar(inicio_hoy),
        "semana": analizar(inicio_semana),
        "mes": analizar(inicio_mes)
    }


# ============================================================
# TEXTO DEL PANEL
# ============================================================

def texto_panel():

    apuestas = cargar_apuestas()

    stats = calcular_estadisticas(
        apuestas
    )

    hoy = stats["hoy"]
    semana = stats["semana"]
    mes = stats["mes"]

    def bloque(titulo, datos):

        return (
            f"<b>{titulo}</b>\n"
            f"🎯 Apuestas: {datos['total']}\n"
            f"🟢 Ganadas: {datos['ganadas']}\n"
            f"🔴 Perdidas: {datos['perdidas']}\n"
            f"⏳ Pendientes: {datos['pendientes']}\n"
            f"💰 Invertido: ${datos['invertido']:,}\n"
            f"📈 Resultado: "
            f"${datos['ganancias']:,.0f}\n"
        )

    texto = (
        "📊 <b>PANEL DE RENDIMIENTO</b>\n\n"
        f"💵 Apuesta fija: <b>${APUESTA:,}</b>\n\n"
        + bloque("📅 HOY", hoy)
        + "\n"
        + bloque("📆 SEMANA", semana)
        + "\n"
        + bloque("🗓️ MES", mes)
    )

    return texto


# ============================================================
# MOSTRAR APUESTAS
# ============================================================

def texto_apuestas():

    apuestas = cargar_apuestas()

    if not apuestas:

        return (
            "🎯 <b>APUESTAS</b>\n\n"
            "No hay apuestas registradas."
        )

    ultimas = apuestas[-15:]

    lineas = [
        "🎯 <b>ÚLTIMAS APUESTAS</b>\n"
    ]

    for apuesta in reversed(ultimas):

        partido = apuesta.get(
            "partido",
            "Partido"
        )

        mercado = apuesta.get(
            "mercado",
            "Mercado"
        )

        resultado = apuesta.get(
            "resultado",
            "PENDIENTE"
        )

        if resultado == "GANADA":
            icono = "🟢"

        elif resultado == "PERDIDA":
            icono = "🔴"

        else:
            icono = "⏳"

        lineas.append(
            f"{icono} <b>{partido}</b>\n"
            f"🎯 {mercado}\n"
            f"💰 ${APUESTA:,}\n"
            f"📌 {resultado}\n"
        )

    return "\n".join(lineas)


# ============================================================
# API-FOOTBALL
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
            f"API-Football: "
            f"{endpoint} "
            f"HTTP {response.status_code}"
        )

        if response.status_code != 200:

            print(
                response.text
            )

            return None

        data = response.json()

        if data.get("errors"):

            print(
                "⚠️ API errors:",
                data["errors"]
            )

        return data

    except Exception as e:

        print(
            "❌ Error API-Football:",
            e
        )

        return None


# ============================================================
# BUSCAR FIXTURE POR EQUIPOS
# ============================================================

def buscar_fixture(
    local,
    visitante
):

    hoy = fecha_local().date()

    fechas = [
        hoy,
        hoy - timedelta(days=1),
        hoy - timedelta(days=2)
    ]

    for fecha in fechas:

        data = api_get(
            "/fixtures",
            {
                "date": fecha.isoformat()
            }
        )

        if not data:
            continue

        for item in data.get(
            "response",
            []
        ):

            equipos = item.get(
                "teams",
                {}
            )

            home = equipos.get(
                "home",
                {}
            ).get(
                "name",
                ""
            )

            away = equipos.get(
                "away",
                {}
            ).get(
                "name",
                ""
            )

            if (
                normalizar(home) == normalizar(local)
                and
                normalizar(away) == normalizar(visitante)
            ):

                return item

    return None


def normalizar(texto):

    texto = (
        texto or ""
    ).lower()

    texto = re.sub(
        r"[^a-z0-9áéíóúüñ ]",
        "",
        texto
    )

    reemplazos = [
        " fc",
        " cf",
        " sc",
        " afc",
        " utd"
    ]

    for x in reemplazos:

        texto = texto.replace(
            x,
            ""
        )

    return " ".join(
        texto.split()
    )


# ============================================================
# COMPROBAR RESULTADOS
# ============================================================

def actualizar_resultados():

    apuestas = cargar_apuestas()

    modificadas = False

    for apuesta in apuestas:

        if apuesta.get(
            "resultado"
        ) != "PENDIENTE":

            continue

        local = apuesta.get(
            "local"
        )

        visitante = apuesta.get(
            "visitante"
        )

        if not local or not visitante:
            continue

        fixture = buscar_fixture(
            local,
            visitante
        )

        if not fixture:
            continue

        fixture_data = fixture.get(
            "fixture",
            {}
        )

        status = fixture_data.get(
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
            continue

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
            continue

        mercado = apuesta.get(
            "mercado",
            ""
        ).lower()

        ganado = evaluar_mercado(
            mercado,
            home_goals,
            away_goals
        )

        if ganado:

            apuesta["resultado"] = "GANADA"

            cuota = apuesta.get(
                "cuota",
                1.0
            )

            apuesta["ganancia"] = (
                APUESTA *
                (cuota - 1)
            )

        else:

            apuesta["resultado"] = "PERDIDA"

            apuesta["ganancia"] = -APUESTA

        apuesta["marcador"] = (
            f"{home_goals}-{away_goals}"
        )

        modificadas = True

        print(
            f"📌 Resultado: "
            f"{apuesta['partido']} "
            f"{apuesta['resultado']}"
        )

        enviar_telegram(
            crear_resultado_mensaje(
                apuesta
            )
        )

    if modificadas:

        guardar_apuestas(
            apuestas
        )


# ============================================================
# EVALUAR MERCADOS
# ============================================================

def evaluar_mercado(
    mercado,
    home,
    away
):

    total = home + away

    if (
        "ambos marcan" in mercado
        or "btts" in mercado
    ):

        return (
            home > 0
            and away > 0
        )

    if "over 2.5" in mercado:

        return total >= 3

    if "over 1.5" in mercado:

        return total >= 2

    if "over 3.5" in mercado:

        return total >= 4

    if "under 2.5" in mercado:

        return total <= 2

    if "under 3.5" in mercado:

        return total <= 3

    if (
        "empate" in mercado
        and "descanso" in mercado
    ):

        return home == away

    if (
        "1x" in mercado
        or "local o empate" in mercado
    ):

        return home >= away

    if (
        "x2" in mercado
        or "visitante o empate" in mercado
    ):

        return away >= home

    if (
        mercado == "local"
        or mercado == "1"
    ):

        return home > away

    if (
        mercado == "visitante"
        or mercado == "2"
    ):

        return away > home

    # Mercado no reconocido
    return False


# ============================================================
# MENSAJE RESULTADO
# ============================================================

def crear_resultado_mensaje(
    apuesta
):

    if apuesta["resultado"] == "GANADA":

        return (
            "🟢 <b>APUESTA GANADA</b>\n\n"
            f"⚽ {apuesta['partido']}\n"
            f"🎯 {apuesta['mercado']}\n"
            f"💰 Apuesta: ${APUESTA:,}\n"
            f"📊 Marcador: {apuesta.get('marcador', '-')}\n"
            f"💵 Ganancia: "
            f"+${apuesta.get('ganancia', 0):,.0f}"
        )

    return (
        "🔴 <b>APUESTA PERDIDA</b>\n\n"
        f"⚽ {apuesta['partido']}\n"
        f"🎯 {apuesta['mercado']}\n"
        f"💰 Apuesta: ${APUESTA:,}\n"
        f"📊 Marcador: {apuesta.get('marcador', '-')}\n"
        f"💵 Resultado: -${APUESTA:,}"
    )


# ============================================================
# PROCESAR ALERTA
# ============================================================

def procesar_alerta(texto):

    texto_limpio = texto.strip()

    print(
        "📨 Alerta recibida:"
    )

    print(
        texto_limpio
    )

    # --------------------------------------------------------
    # BUSCAR PARTIDO
    # --------------------------------------------------------

    partido = None

    patron_vs = re.search(
        r"(.+?)\s+(?:vs|v|-)\s+(.+)",
        texto_limpio,
        re.IGNORECASE
    )

    if patron_vs:

        local = patron_vs.group(1).strip()
        visitante = patron_vs.group(2).strip()

        partido = (
            f"{local} vs {visitante}"
        )

    else:

        local = ""
        visitante = ""

    # --------------------------------------------------------
    # BUSCAR CUOTA
    # --------------------------------------------------------

    cuota = 1.0

    patron_cuota = re.search(
        r"(?:cuota|odd|odds)\s*[:=]?\s*(\d+(?:\.\d+)?)",
        texto_limpio,
        re.IGNORECASE
    )

    if patron_cuota:

        cuota = float(
            patron_cuota.group(1)
        )

    # --------------------------------------------------------
    # MERCADO
    # --------------------------------------------------------

    mercados = [
        "ambos marcan",
        "btts",
        "over 1.5",
        "over 2.5",
        "over 3.5",
        "under 2.5",
        "under 3.5",
        "empate al descanso",
        "empate descanso",
        "local",
        "visitante",
        "1x",
        "x2"
    ]

    mercado = "Mercado no identificado"

    for m in mercados:

        if m.lower() in texto_limpio.lower():

            mercado = m.upper()

            break

    if not local or not visitante:

        enviar_telegram(
            "⚠️ No pude identificar "
            "correctamente el partido "
            "en la alerta."
        )

        return

    apuestas = cargar_apuestas()

    apuesta = {
        "id": int(time.time()),
        "fecha": fecha_local().isoformat(),
        "local": local,
        "visitante": visitante,
        "partido": partido,
        "mercado": mercado,
        "cuota": cuota,
        "apuesta": APUESTA,
        "resultado": "PENDIENTE",
        "ganancia": 0
    }

    apuestas.append(
        apuesta
    )

    guardar_apuestas(
        apuestas
    )

    enviar_telegram(
        "⏳ <b>APUESTA REGISTRADA</b>\n\n"
        f"⚽ {partido}\n"
        f"🎯 Mercado: {mercado}\n"
        f"💰 Apuesta: ${APUESTA:,}\n"
        f"📌 Estado: PENDIENTE"
    )


# ============================================================
# COMANDOS
# ============================================================

def procesar_comando(
    chat_id,
    message_id,
    texto
):

    texto = texto.lower().strip()

    if texto == "/panel":

        editar_mensaje(
            chat_id,
            message_id,
            texto_panel(),
            botones_panel()
        )

    elif texto == "/apuestas":

        editar_mensaje(
            chat_id,
            message_id,
            texto_apuestas(),
            botones_panel()
        )


# ============================================================
# CALLBACKS
# ============================================================

def procesar_callback(
    callback
):

    callback_id = callback.get(
        "id"
    )

    data = callback.get(
        "data"
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

    telegram(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )

    if data in [
        "panel",
        "hoy",
        "semana",
        "mes"
    ]:

        editar_mensaje(
            chat_id,
            message_id,
            texto_panel(),
            botones_panel()
        )

    elif data == "apuestas":

        editar_mensaje(
            chat_id,
            message_id,
            texto_apuestas(),
            botones_panel()
        )


# ============================================================
# LEER TELEGRAM
# ============================================================

def leer_telegram(offset=None):

    params = {
        "timeout": 5
    }

    if offset is not None:

        params["offset"] = offset

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/getUpdates"
    )

    try:

        response = requests.get(
            url,
            params=params,
            timeout=15
        )

        if response.status_code != 200:

            return []

        return response.json().get(
            "result",
            []
        )

    except Exception as e:

        print(
            "❌ Telegram getUpdates:",
            e
        )

        return []


# ============================================================
# CREAR RESULTADO
# ============================================================

def ejecutar_bot():

    print(
        "🤖 Bot iniciado."
    )

    offset = None

    ultima_revision = 0

    while True:

        try:

            # ----------------------------------------------
            # REVISAR RESULTADOS CADA 2 MINUTOS
            # ----------------------------------------------

            ahora = time.time()

            if ahora - ultima_revision >= 120:

                actualizar_resultados()

                ultima_revision = ahora

            # ----------------------------------------------
            # TELEGRAM
            # ----------------------------------------------

            updates = leer_telegram(
                offset
            )

            for update in updates:

                offset = (
                    update["update_id"] + 1
                )

                # ------------------------------------------
                # MENSAJE
                # ------------------------------------------

                if "message" in update:

                    message = update[
                        "message"
                    ]

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

                    message_id = message.get(
                        "message_id"
                    )

                    # Solo nuestro chat
                    if str(chat_id) != str(
                        CHAT_ID
                    ):

                        continue

                    if texto.startswith("/"):

                        procesar_comando(
                            chat_id,
                            message_id,
                            texto
                        )

                    else:

                        # Permite recibir una alerta
                        # enviada directamente al bot
                        procesar_alerta(
                            texto
                        )

                # ------------------------------------------
                # BOTÓN
                # ------------------------------------------

                elif "callback_query" in update:

                    procesar_callback(
                        update[
                            "callback_query"
                        ]
                    )

            time.sleep(1)

        except KeyboardInterrupt:

            print(
                "🛑 Bot detenido."
            )

            break

        except Exception as e:

            print(
                "❌ Error principal:",
                e
            )

            time.sleep(5)


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":

    ejecutar_bot()