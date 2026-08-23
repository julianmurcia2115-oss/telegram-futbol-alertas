import os
import re
import json
import requests
from datetime import datetime, timezone

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SIGNALS_FILE = "signals.json"
OFFSET_FILE = "telegram_offset.json"

BET_AMOUNT = 5000


# =========================================================
# TELEGRAM
# =========================================================

def telegram_request(method, data=None):

    try:
        response = requests.post(
            f"{TELEGRAM_URL}/{method}",
            data=data or {},
            timeout=30
        )

        result = response.json()

        print(
            f"Telegram {method}: "
            f"{result.get('ok')} "
            f"{result}"
        )

        return result

    except Exception as e:

        print(
            f"ERROR TELEGRAM {method}:",
            e
        )

        return {
            "ok": False,
            "error": str(e)
        }


def send_message(
    chat_id,
    text,
    keyboard=None
):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard is not None:

        data["reply_markup"] = json.dumps(
            {
                "inline_keyboard": keyboard
            },
            ensure_ascii=False
        )

    return telegram_request(
        "sendMessage",
        data
    )


def edit_message(
    chat_id,
    message_id,
    text,
    keyboard=None
):

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    if keyboard is not None:

        data["reply_markup"] = json.dumps(
            {
                "inline_keyboard": keyboard
            },
            ensure_ascii=False
        )

    return telegram_request(
        "editMessageText",
        data
    )


def answer_callback(callback_id):

    return telegram_request(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


# =========================================================
# ARCHIVOS
# =========================================================

def load_signals():

    if not os.path.exists(
        SIGNALS_FILE
    ):

        return []

    try:

        with open(
            SIGNALS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            if isinstance(data, list):

                return data

    except Exception as e:

        print(
            "Error leyendo signals.json:",
            e
        )

    return []


def save_signals(signals):

    try:

        with open(
            SIGNALS_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                signals,
                f,
                ensure_ascii=False,
                indent=2
            )

        return True

    except Exception as e:

        print(
            "Error guardando signals.json:",
            e
        )

        return False


# =========================================================
# OFFSET
# =========================================================

def load_offset():

    if not os.path.exists(
        OFFSET_FILE
    ):

        return None

    try:

        with open(
            OFFSET_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

            return data.get(
                "offset"
            )

    except Exception as e:

        print(
            "Error leyendo offset:",
            e
        )

        return None


def save_offset(offset):

    try:

        with open(
            OFFSET_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                {
                    "offset": offset
                },
                f,
                indent=2
            )

        return True

    except Exception as e:

        print(
            "Error guardando offset:",
            e
        )

        return False


# =========================================================
# BOTONES
# =========================================================

def main_keyboard():

    return [

        [
            {
                "text": "📊 Rendimiento",
                "callback_data": "rendimiento"
            },
            {
                "text": "🎯 Estrategias",
                "callback_data": "estrategias"
            }
        ],

        [
            {
                "text": "📅 Calendario",
                "callback_data": "calendario"
            },
            {
                "text": "⏳ Pendientes",
                "callback_data": "pendientes"
            }
        ],

        [
            {
                "text": "💰 Ganancias",
                "callback_data": "ganancias"
            },
            {
                "text": "📈 Estadísticas",
                "callback_data": "estadisticas"
            }
        ],

        [
            {
                "text": "⚙️ Configuración",
                "callback_data": "configuracion"
            }
        ]

    ]


def back_keyboard():

    return [

        [
            {
                "text": "⬅️ Volver al panel",
                "callback_data": "inicio"
            }
        ]

    ]


# =========================================================
# EXTRACCIÓN DE DATOS
# =========================================================

def extract(
    text,
    patterns,
    default="No identificado"
):

    if isinstance(
        patterns,
        str
    ):

        patterns = [
            patterns
        ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(
                1
            ).strip()

    return default


def extract_strategy(text):

    result = extract(
        text,
        [
            r"Resultado\s*deseado\s*:\s*(.+)",
            r"Estrategia\s*:\s*(.+)",
            r"🎯\s*(.+)"
        ],
        ""
    )

    if result:

        return result

    lower = text.lower()

    if "más de 3.5" in lower:

        return "Más de 3.5 goles"

    if "más de 2.5" in lower:

        return "Más de 2.5 goles"

    if "ambos marcan" in lower:

        return "Ambos Marcan"

    if "btts" in lower:

        return "Ambos Marcan"

    if "victoria local" in lower:

        return "Victoria Local"

    if "victoria visitante" in lower:

        return "Victoria Visitante"

    return "SIN ESTRATEGIA"


def extract_odds(text):

    value = extract(
        text,
        [
            r"bet365\s*:\s*([\d.,]+)",
            r"cuota\s*:\s*([\d.,]+)"
        ],
        ""
    )

    if not value:

        return None

    try:

        return float(
            value.replace(
                ",",
                "."
            )
        )

    except Exception:

        return None


# =========================================================
# DETECTAR SEÑAL
# =========================================================

def is_bet_alert(text):

    if not text:

        return False

    if text.startswith("/"):

        return False

    lower = text.lower()

    keywords = [

        "🏆",
        "🆚",
        "🗓",
        "liga:",
        "partido:",
        "fecha:",
        "estrategia:",
        "resultado deseado:",
        "bet365:",
        "cuota:",
        "betmines",
        "btts",
        "más de 2.5",
        "más de 3.5",
        "ambos marcan"
    ]

    matches = 0

    for keyword in keywords:

        if keyword.lower() in lower:

            matches += 1

    return matches >= 2


# =========================================================
# REGISTRAR SEÑAL
# =========================================================

def register_signal(text):

    signals = load_signals()

    signal = {

        "id":
            len(signals) + 1,

        "registered_at":
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "league":
            extract(
                text,
                [
                    r"🏆\s*(.+)",
                    r"Liga\s*:\s*(.+)"
                ]
            ),

        "match":
            extract(
                text,
                [
                    r"🆚\s*(.+)",
                    r"Partido\s*:\s*(.+)"
                ]
            ),

        "date":
            extract(
                text,
                [
                    r"🗓\s*(.+)",
                    r"Fecha\s*:\s*(.+)"
                ]
            ),

        "strategy":
            extract_strategy(
                text
            ),

        "odds":
            extract_odds(
                text
            ),

        "result":
            "PENDIENTE",

        "raw_message":
            text
    }

    signals.append(
        signal
    )

    save_signals(
        signals
    )

    return signal


# =========================================================
# ESTADÍSTICAS
# =========================================================

def calculate_stats(
    signals
):

    won = 0
    lost = 0
    pending = 0
    profit = 0

    for signal in signals:

        result = signal.get(
            "result",
            "PENDIENTE"
        )

        odds = signal.get(
            "odds"
        )

        if result == "GANADA":

            won += 1

            if odds:

                profit += (
                    BET_AMOUNT
                    *
                    (
                        odds - 1
                    )
                )

            else:

                profit += BET_AMOUNT

        elif result == "PERDIDA":

            lost += 1

            profit -= BET_AMOUNT

        else:

            pending += 1

    finished = won + lost

    if finished:

        effectiveness = (
            won / finished
        ) * 100

    else:

        effectiveness = 0

    total_staked = (
        finished
        *
        BET_AMOUNT
    )

    if total_staked:

        roi = (
            profit
            /
            total_staked
        ) * 100

    else:

        roi = 0

    return {

        "total":
            len(signals),

        "won":
            won,

        "lost":
            lost,

        "pending":
            pending,

        "effectiveness":
            effectiveness,

        "profit":
            profit,

        "roi":
            roi
    }


# =========================================================
# PANEL PRINCIPAL
# =========================================================

def dashboard():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    return f"""
🏆 APUESTASMURCIA
━━━━━━━━━━━━━━━━━━━━

📊 CENTRO DE CONTROL

📥 Señales
{stats['total']}

⏳ Pendientes
{stats['pending']}

✅ Ganadas
{stats['won']}

❌ Perdidas
{stats['lost']}

━━━━━━━━━━━━━━━━━━━━

🎯 Efectividad
{stats['effectiveness']:.1f}%

📈 ROI
{stats['roi']:.1f}%

💰 Ganancia
${stats['profit']:,.0f} COP

💵 Apuesta fija
${BET_AMOUNT:,.0f} COP

━━━━━━━━━━━━━━━━━━━━

👇 Selecciona una opción:
"""


# =========================================================
# RENDIMIENTO
# =========================================================

def rendimiento():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    return f"""
📊 RENDIMIENTO
━━━━━━━━━━━━━━━━━━━━

📥 SEÑALES
{stats['total']}

✅ GANADAS
{stats['won']}

❌ PERDIDAS
{stats['lost']}

⏳ PENDIENTES
{stats['pending']}

━━━━━━━━━━━━━━━━━━━━

🎯 EFECTIVIDAD
{stats['effectiveness']:.1f}%

📈 ROI
{stats['roi']:.1f}%

💰 GANANCIA
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━

💵 Apuesta por señal:
${BET_AMOUNT:,.0f} COP
"""


# =========================================================
# ESTRATEGIAS
# =========================================================

def estrategias():

    signals = load_signals()

    groups = {}

    for signal in signals:

        strategy = signal.get(
            "strategy",
            "SIN ESTRATEGIA"
        )

        if strategy not in groups:

            groups[strategy] = []

        groups[
            strategy
        ].append(
            signal
        )

    if not groups:

        return (
            "🎯 No hay estrategias registradas."
        )

    text = """
🎯 ESTRATEGIAS
━━━━━━━━━━━━━━━━━━━━
"""

    for strategy, items in groups.items():

        stats = calculate_stats(
            items
        )

        text += f"""

🎯 {strategy}

📥 Señales: {stats['total']}
✅ Ganadas: {stats['won']}
❌ Perdidas: {stats['lost']}
⏳ Pendientes: {stats['pending']}

🎯 Efectividad:
{stats['effectiveness']:.1f}%

📈 ROI:
{stats['roi']:.1f}%

💰 Ganancia:
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
"""

    return text


# =========================================================
# PENDIENTES
# =========================================================

def pendientes():

    signals = load_signals()

    pending = [

        s for s in signals

        if s.get(
            "result",
            "PENDIENTE"
        ) == "PENDIENTE"

    ]

    if not pending:

        return """
⏳ PENDIENTES

🟢 No tienes apuestas pendientes.
"""

    text = """
⏳ APUESTAS PENDIENTES
━━━━━━━━━━━━━━━━━━━━
"""

    for signal in pending[:30]:

        odds = signal.get(
            "odds"
        )

        odds_text = (
            f"{odds:.2f}"
            if odds
            else "N/D"
        )

        text += f"""

🆔 #{signal.get('id')}

🏆 {signal.get('league')}

⚽ {signal.get('match')}

🎯 {signal.get('strategy')}

💰 Cuota: {odds_text}

━━━━━━━━━━━━━━━━━━━━
"""

    if len(pending) > 30:

        text += (
            f"\n📌 Hay "
            f"{len(pending) - 30} "
            f"pendientes adicionales."
        )

    return text


# =========================================================
# CALENDARIO
# =========================================================

def calendario():

    signals = load_signals()

    days = {}

    for signal in signals:

        registered = signal.get(
            "registered_at",
            ""
        )

        day = registered[:10]

        if not day:

            continue

        if day not in days:

            days[day] = []

        days[
            day
        ].append(
            signal
        )

    if not days:

        return (
            "📅 No hay datos para el calendario."
        )

    text = """
📅 CALENDARIO
━━━━━━━━━━━━━━━━━━━━
"""

    for day in sorted(
        days.keys(),
        reverse=True
    ):

        stats = calculate_stats(
            days[day]
        )

        if stats["profit"] > 0:

            icon = "🟢"

        elif stats["profit"] < 0:

            icon = "🔴"

        else:

            icon = "🟡"

        text += f"""

{icon} {day}

📥 Señales: {stats['total']}
✅ {stats['won']}
❌ {stats['lost']}
⏳ {stats['pending']}

💰 ${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
"""

    return text


# =========================================================
# GANANCIAS
# =========================================================

def ganancias():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    finished = (
        stats["won"]
        +
        stats["lost"]
    )

    invested = (
        finished
        *
        BET_AMOUNT
    )

    return f"""
💰 GANANCIAS
━━━━━━━━━━━━━━━━━━━━

💵 APUESTA FIJA
${BET_AMOUNT:,.0f} COP

📊 APUESTAS FINALIZADAS
{finished}

💸 CAPITAL APOSTADO
${invested:,.0f} COP

━━━━━━━━━━━━━━━━━━━━

💰 GANANCIA/PÉRDIDA
${stats['profit']:,.0f} COP

📈 ROI
{stats['roi']:.1f}%

🎯 EFECTIVIDAD
{stats['effectiveness']:.1f}%

━━━━━━━━━━━━━━━━━━━━
"""


# =========================================================
# ESTADÍSTICAS
# =========================================================

def estadisticas():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    odds = []

    for signal in signals:

        value = signal.get(
            "odds"
        )

        if isinstance(
            value,
            (int, float)
        ):

            odds.append(
                value
            )

    if odds:

        average_odds = (
            sum(odds)
            /
            len(odds)
        )

    else:

        average_odds = 0

    return f"""
📈 ESTADÍSTICAS
━━━━━━━━━━━━━━━━━━━━

📥 Total señales
{stats['total']}

✅ Ganadas
{stats['won']}

❌ Perdidas
{stats['lost']}

⏳ Pendientes
{stats['pending']}

━━━━━━━━━━━━━━━━━━━━

🎯 Efectividad
{stats['effectiveness']:.1f}%

📈 ROI
{stats['roi']:.1f}%

🎲 Cuota promedio
{average_odds:.2f}

💰 Ganancia
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
"""


# =========================================================
# CONFIGURACIÓN
# =========================================================

def configuracion():

    return f"""
⚙️ CONFIGURACIÓN
━━━━━━━━━━━━━━━━━━━━

💵 Apuesta fija

${BET_AMOUNT:,.0f} COP

📥 Recepción de señales

Telegram

💾 Archivo de señales

signals.json

🔄 Control de mensajes

telegram_offset.json

━━━━━━━━━━━━━━━━━━━━

Esta sección muestra
la configuración actual.
"""


# =========================================================
# CALLBACKS DE BOTONES
# =========================================================

def process_callback(
    callback
):

    callback_id = callback.get(
        "id"
    )

    data = callback.get(
        "data",
        ""
    )

    message = callback.get(
        "message"
    )

    if not message:

        return

    chat_id = message[
        "chat"
    ][
        "id"
    ]

    message_id = message[
        "message_id"
    ]

    answer_callback(
        callback_id
    )

    if data == "inicio":

        edit_message(
            chat_id,
            message_id,
            dashboard(),
            main_keyboard()
        )

        return

    if data == "rendimiento":

        edit_message(
            chat_id,
            message_id,
            rendimiento(),
            back_keyboard()
        )

        return

    if data == "estrategias":

        edit_message(
            chat_id,
            message_id,
            estrategias(),
            back_keyboard()
        )

        return

    if data == "calendario":

        edit_message(
            chat_id,
            message_id,
            calendario(),
            back_keyboard()
        )

        return

    if data == "pendientes":

        edit_message(
            chat_id,
            message_id,
            pendientes(),
            back_keyboard()
        )

        return

    if data == "ganancias":

        edit_message(
            chat_id,
            message_id,
            ganancias(),
            back_keyboard()
        )

        return

    if data == "estadisticas":

        edit_message(
            chat_id,
            message_id,
            estadisticas(),
            back_keyboard()
        )

        return

    if data == "configuracion":

        edit_message(
            chat_id,
            message_id,
            configuracion(),
            back_keyboard()
        )

        return


# =========================================================
# COMANDOS
# =========================================================

def process_message(
    message
):

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get(
        "id"
    )

    text = message.get(
        "text",
        ""
    ).strip()

    if not chat_id:

        return

    if not text:

        return

    print(
        "Procesando:",
        text
    )

    command = text.split()[0].lower()

    # START

    if command == "/start":

        send_message(
            chat_id,
            dashboard(),
            main_keyboard()
        )

        return

    # PANEL

    if command == "/panel":

        result = send_message(
            chat_id,
            dashboard(),
            main_keyboard()
        )

        print(
            "Resultado panel:",
            result
        )

        return

    # COMANDOS ANTIGUOS

    if command == "/estrategias":

        send_message(
            chat_id,
            estrategias(),
            back_keyboard()
        )

        return

    if command == "/pendientes":

        send_message(
            chat_id,
            pendientes(),
            back_keyboard()
        )

        return

    if command == "/calendario":

        send_message(
            chat_id,
            calendario(),
            back_keyboard()
        )

        return

    # COMANDOS DESCONOCIDOS

    if text.startswith("/"):

        print(
            "Comando ignorado:",
            text
        )

        return

    # ALERTA

    if not is_bet_alert(
        text
    ):

        print(
            "Mensaje ignorado:",
            text[:100]
        )

        return

    signal = register_signal(
        text
    )

    odds = signal.get(
        "odds"
    )

    if odds:

        odds_text = f"{odds:.2f}"

    else:

        odds_text = "N/D"

    send_message(
        chat_id,
        f"""
📥 SEÑAL REGISTRADA
━━━━━━━━━━━━━━━━━━━━

🆔 #{signal['id']}

🏆 {signal['league']}

⚽ {signal['match']}

📅 {signal['date']}

🎯 {signal['strategy']}

💰 Cuota: {odds_text}

⏳ ESTADO: PENDIENTE

━━━━━━━━━━━━━━━━━━━━

📊 Usa /panel para abrir
el centro de control.
"""
    )


# =========================================================
# TELEGRAM UPDATES
# =========================================================

def get_updates(
    offset=None
):

    params = {
        "timeout": 5,
        "limit": 100
    }

    if offset is not None:

        params[
            "offset"
        ] = offset

    try:

        response = requests.get(
            f"{TELEGRAM_URL}/getUpdates",
            params=params,
            timeout=15
        )

        result = response.json()

        print(
            "getUpdates:",
            result
        )

        if not result.get(
            "ok"
        ):

            return []

        return result.get(
            "result",
            []
        )

    except Exception as e:

        print(
            "ERROR getUpdates:",
            e
        )

        return []


# =========================================================
# MAIN
# =========================================================

def main():

    print(
        "===================================="
    )

    print(
        "       APUESTASMURCIA BOT"
    )

    print(
        "       DASHBOARD CON BOTONES"
    )

    print(
        "===================================="
    )

    offset = load_offset()

    print(
        "Offset:",
        offset
    )

    updates = get_updates(
        offset
    )

    print(
        "Mensajes encontrados:",
        len(updates)
    )

    for update in updates:

        update_id = update.get(
            "update_id"
        )

        try:

            if "message" in update:

                process_message(
                    update["message"]
                )

            elif "callback_query" in update:

                print(
                    "Botón pulsado:",
                    update[
                        "callback_query"
                    ].get("data")
                )

                process_callback(
                    update["callback_query"]
                )

        except Exception as e:

            print(
                "ERROR procesando update:",
                e
            )

        # MUY IMPORTANTE:
        # Guardamos el offset después
        # de procesar el mensaje/botón.

        if update_id is not None:

            save_offset(
                update_id + 1
            )

    print(
        "===================================="
    )

    print(
        "Ejecución terminada."
    )

    print(
        "===================================="
    )


if __name__ == "__main__":

    main()