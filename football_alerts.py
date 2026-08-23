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

SIGNALS_FILE = "signals.json"
STATE_FILE = "bot_state.json"

STAKE = 5000

# Colombia
COLOMBIA_TZ = timezone(timedelta(hours=-5))

# ============================================================
# VALIDACIÓN
# ============================================================

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADO")
    raise SystemExit(1)

if not CHAT_ID:
    print("❌ TELEGRAM_CHAT_ID NO CONFIGURADO")
    raise SystemExit(1)

print("====================================")
print("⚽ FOOTBALL ALERTS")
print("====================================")
print("🤖 Telegram: CONFIGURADO")
print("💬 Chat ID: CONFIGURADO")
print("💰 Apuesta: $5.000 COP")
print("====================================")


# ============================================================
# ARCHIVOS
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

    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(
            datos,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(temporal, archivo)


def cargar_apuestas():
    datos = cargar_json(SIGNALS_FILE, [])

    if isinstance(datos, list):
        return datos

    if isinstance(datos, dict):
        if "signals" in datos:
            return datos["signals"]

        if "apuestas" in datos:
            return datos["apuestas"]

    return []


def guardar_apuestas(apuestas):
    guardar_json(SIGNALS_FILE, apuestas)


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


def enviar(mensaje):

    return telegram_api(
        "sendMessage",
        {
            "chat_id": CHAT_ID,
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
    ).strftime("%Y-%m-%d %H:%M:%S")


def normalizar(texto):

    if not texto:
        return ""

    texto = texto.lower()

    reemplazos = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n"
    }

    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


# ============================================================
# IDENTIFICAR ESTRATEGIA
# ============================================================

def identificar_estrategia(texto):

    t = normalizar(texto)

    estrategias = [
        (
            "BTTS",
            [
                "ambos equipos marcan",
                "ambos marcan",
                "btts",
                "both teams to score"
            ]
        ),
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
            "Empate 1T",
            [
                "empate 1t",
                "empate al descanso",
                "empate descanso",
                "half time draw"
            ]
        ),
        (
            "1X2",
            [
                "1x2"
            ]
        )
    ]

    for nombre, palabras in estrategias:

        for palabra in palabras:

            if palabra in t:
                return nombre

    return "Otra"


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
        r"pinnacle\s*:\s*([0-9]+(?:[.,][0-9]+)?)",
        r"cuota\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",
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
                    resultado.group(1).replace(",", ".")
                )
            except:
                pass

    return None


# ============================================================
# CREAR APUESTA
# ============================================================

def crear_apuesta(texto):

    home, away = extraer_partido(texto)

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

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    apuesta = {

        "id": int(
            time.time() * 1000
        ),

        "fecha_registro": ahora_colombia(),

        "timestamp": timestamp,

        "home": home,

        "away": away,

        "liga": liga,

        "fecha_partido": fecha_partido,

        "estrategia": estrategia,

        "cuota": cuota,

        "stake": STAKE,

        "resultado": "pendiente",

        "ganancia": 0,

        "texto_original": texto
    }

    return apuesta


# ============================================================
# EVITAR DUPLICADOS
# ============================================================

def apuesta_duplicada(apuestas, nueva):

    for apuesta in apuestas:

        if (
            normalizar(
                apuesta.get("home", "")
            )
            ==
            normalizar(
                nueva.get("home", "")
            )
            and
            normalizar(
                apuesta.get("away", "")
            )
            ==
            normalizar(
                nueva.get("away", "")
            )
            and
            apuesta.get("estrategia")
            ==
            nueva.get("estrategia")
            and
            apuesta.get("fecha_partido")
            ==
            nueva.get("fecha_partido")
        ):

            return True

    return False


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
            "ℹ️ Apuesta duplicada. "
            "No se registra nuevamente."
        )

        return False

    apuestas.append(
        nueva
    )

    guardar_apuestas(
        apuestas
    )

    print(
        f"✅ Apuesta registrada: "
        f"{nueva['home']} vs {nueva['away']}"
    )

    mensaje = (
        "✅ <b>APUESTA REGISTRADA</b>\n\n"
        f"⚽ {nueva['home']} - "
        f"{nueva['away']}\n\n"
        f"🏆 {nueva['liga']}\n"
        f"🎯 {nueva['estrategia']}\n"
        f"💰 Apuesta: $5.000 COP\n"
        f"📌 Estado: 🟡 PENDIENTE"
    )

    enviar(
        mensaje
    )

    return True


# ============================================================
# ESTADÍSTICAS
# ============================================================

def calcular_estadisticas(apuestas):

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

            ganancia -= STAKE

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
        "total": len(apuestas),
        "ganadas": ganadas,
        "perdidas": perdidas,
        "pendientes": pendientes,
        "ganancia": ganancia,
        "efectividad": efectividad,
        "roi": roi
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

    limite = ahora - timedelta(
        days=dias
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

        except:

            continue

        if fecha_dt >= limite:

            seleccionadas.append(
                apuesta
            )

    return calcular_estadisticas(
        seleccionadas
    )


# ============================================================
# ESTRATEGIAS
# ============================================================

def estrategias(apuestas):

    datos = {}

    for apuesta in apuestas:

        estrategia = apuesta.get(
            "estrategia",
            "Otra"
        )

        if estrategia not in datos:

            datos[estrategia] = {
                "total": 0,
                "ganadas": 0,
                "perdidas": 0,
                "pendientes": 0,
                "ganancia": 0
            }

        datos[estrategia]["total"] += 1

        resultado = apuesta.get(
            "resultado",
            "pendiente"
        )

        if resultado == "ganada":

            datos[estrategia]["ganadas"] += 1

            datos[estrategia]["ganancia"] += float(
                apuesta.get(
                    "ganancia",
                    0
                )
            )

        elif resultado == "perdida":

            datos[estrategia]["perdidas"] += 1

            datos[estrategia]["ganancia"] -= STAKE

        else:

            datos[estrategia]["pendientes"] += 1

    resultado = []

    for nombre, datos_estrategia in datos.items():

        cerradas = (
            datos_estrategia["ganadas"] +
            datos_estrategia["perdidas"]
        )

        if cerradas:

            efectividad = (
                datos_estrategia["ganadas"] /
                cerradas
            ) * 100

        else:

            efectividad = 0

        resultado.append(
            (
                nombre,
                datos_estrategia,
                efectividad
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

        "💰 <b>Capital por apuesta:</b> "
        "$5.000 COP\n\n"

        f"🎯 <b>Total apuestas:</b> "
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
        f"💵 ${mes['ganancia']:,.0f} COP\n"
    )

    return texto


# ============================================================
# ESTRATEGIAS MÁS EFICIENTES
# ============================================================

def crear_panel_estrategias():

    apuestas = cargar_apuestas()

    datos = estrategias(
        apuestas
    )

    if not datos:

        return (
            "🏆 <b>ESTRATEGIAS</b>\n\n"
            "Todavía no hay estrategias registradas."
        )

    mensaje = (
        "🏆 <b>ESTRATEGIAS MÁS EFICIENTES</b>\n\n"
    )

    posicion = 1

    for nombre, datos_estrategia, efectividad in datos[:10]:

        mensaje += (
            f"{posicion}. <b>{nombre}</b>\n"
            f"   🎯 Apuestas: "
            f"{datos_estrategia['total']}\n"
            f"   🟢 Ganadas: "
            f"{datos_estrategia['ganadas']}\n"
            f"   🔴 Perdidas: "
            f"{datos_estrategia['perdidas']}\n"
            f"   📈 Efectividad: "
            f"{efectividad:.1f}%\n"
            f"   💵 Resultado: "
            f"${datos_estrategia['ganancia']:,.0f} COP\n\n"
        )

        posicion += 1

    return mensaje


# ============================================================
# LISTA DE PENDIENTES
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
            "🟡 <b>APUESTAS PENDIENTES</b>\n\n"
            "No hay apuestas pendientes."
        )

    mensaje = (
        "🟡 <b>APUESTAS PENDIENTES</b>\n\n"
    )

    for apuesta in pendientes[-15:]:

        mensaje += (
            f"🆔 {apuesta['id']}\n"
            f"⚽ {apuesta['home']} - "
            f"{apuesta['away']}\n"
            f"🎯 {apuesta['estrategia']}\n"
            f"💰 $5.000 COP\n\n"
        )

    return mensaje


# ============================================================
# BOTONES
# ============================================================

def panel_con_botones():

    texto = crear_panel()

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "📊 Actualizar",
                    "callback_data": "panel"
                },
                {
                    "text": "🏆 Estrategias",
                    "callback_data": "estrategias"
                }
            ],
            [
                {
                    "text": "🟡 Pendientes",
                    "callback_data": "pendientes"
                }
            ]
        ]
    }

    return texto, json.dumps(
        keyboard,
        ensure_ascii=False
    )


def enviar_panel(chat_id):

    texto, keyboard = panel_con_botones()

    telegram_api(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": "HTML",
            "reply_markup": keyboard
        }
    )


# ============================================================
# CALLBACKS
# ============================================================

def responder_callback(
    callback
):

    callback_id = callback.get(
        "id"
    )

    data = callback.get(
        "data"
    )

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

    if data == "panel":

        enviar_panel(
            chat_id
        )

    elif data == "estrategias":

        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text":
                    crear_panel_estrategias(),
                "parse_mode": "HTML"
            }
        )

    elif data == "pendientes":

        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text":
                    crear_pendientes(),
                "parse_mode": "HTML"
            }
        )


# ============================================================
# COMANDOS
# ============================================================

def procesar_comando(
    chat_id,
    texto
):

    comando = texto.split()[0].lower()

    if comando == "/start":

        enviar(
            "⚽ <b>FOOTBALL ALERTS</b>\n\n"
            "Bot conectado correctamente.\n\n"
            "📊 Usa /panel para ver "
            "las estadísticas."
        )

    elif comando == "/panel":

        enviar_panel(
            chat_id
        )

    elif comando == "/estrategias":

        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text":
                    crear_panel_estrategias(),
                "parse_mode": "HTML"
            }
        )

    elif comando == "/pendientes":

        telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text":
                    crear_pendientes(),
                "parse_mode": "HTML"
            }
        )


# ============================================================
# RECIBIR ALERTAS
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

    # Solo aceptar mensajes del usuario configurado
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

    # Si no es comando, se considera alerta BetMines
    registrar_apuesta(
        texto
    )


# ============================================================
# LOOP TELEGRAM
# ============================================================

def iniciar_bot():

    offset = None

    print(
        "🤖 Esperando alertas de BetMines..."
    )

    while True:

        try:

            parametros = {
                "timeout": 30
            }

            if offset is not None:
                parametros["offset"] = offset

            respuesta = telegram_api(
                "getUpdates",
                parametros
            )

            if not respuesta:

                time.sleep(5)
                continue

            resultados = respuesta.get(
                "result",
                []
            )

            for update in resultados:

                offset = update["update_id"] + 1

                if "callback_query" in update:

                    responder_callback(
                        update["callback_query"]
                    )

                elif "message" in update:

                    procesar_mensaje(
                        update["message"]
                    )

        except Exception as e:

            print(
                f"❌ Error principal: {e}"
            )

            time.sleep(5)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    iniciar_bot()