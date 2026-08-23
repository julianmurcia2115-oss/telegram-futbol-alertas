import os
import re
import json
import base64
import requests
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SIGNALS_FILE = "signals.json"
OFFSET_FILE = "telegram_offset.json"

BET_AMOUNT = 5000


# ============================================================
# TELEGRAM
# ============================================================

def telegram_request(method, data=None):

    try:
        response = requests.post(
            f"{TELEGRAM_URL}/{method}",
            data=data or {},
            timeout=30
        )

        result = response.json()

        print(
            f"Telegram {method}:",
            result.get("ok")
        )

        return result

    except Exception as e:

        print(
            f"Error Telegram {method}:",
            e
        )

        return {
            "ok": False
        }


def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:

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

    if keyboard:

        data["reply_markup"] = json.dumps(
            {
                "inline_keyboard": keyboard
            },
            ensure_ascii=False
        )

    else:

        data["reply_markup"] = json.dumps(
            {
                "inline_keyboard": []
            }
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


# ============================================================
# GITHUB
# ============================================================

def github_headers():

    return {
        "Authorization":
            f"Bearer {GITHUB_TOKEN}",

        "Accept":
            "application/vnd.github+json",

        "X-GitHub-Api-Version":
            "2022-11-28"
    }


def github_get_file(filename):

    if not GITHUB_TOKEN:
        return None, None

    if not GITHUB_REPOSITORY:
        return None, None

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPOSITORY}/contents/{filename}"
    )

    try:

        response = requests.get(
            url,
            headers=github_headers(),
            timeout=30
        )

        if not response.ok:

            print(
                "GitHub GET:",
                response.status_code
            )

            return None, None

        data = response.json()

        content = base64.b64decode(
            data["content"]
        ).decode("utf-8")

        return (
            content,
            data.get("sha")
        )

    except Exception as e:

        print(
            "Error GitHub:",
            e
        )

        return None, None


def github_save_file(
    filename,
    content,
    message
):

    if not GITHUB_TOKEN:
        return False

    if not GITHUB_REPOSITORY:
        return False

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPOSITORY}/contents/{filename}"
    )

    try:

        _, sha = github_get_file(
            filename
        )

        encoded = base64.b64encode(
            content.encode("utf-8")
        ).decode("utf-8")

        payload = {
            "message": message,
            "content": encoded
        }

        if sha:

            payload["sha"] = sha

        response = requests.put(
            url,
            headers=github_headers(),
            json=payload,
            timeout=30
        )

        if response.ok:

            print(
                filename,
                "guardado."
            )

            return True

        print(
            "GitHub PUT:",
            response.status_code,
            response.text
        )

        return False

    except Exception as e:

        print(
            "Error guardando:",
            e
        )

        return False


# ============================================================
# SIGNALS
# ============================================================

def load_signals():

    content, _ = github_get_file(
        SIGNALS_FILE
    )

    if content:

        try:

            return json.loads(
                content
            )

        except Exception:
            pass

    if os.path.exists(
        SIGNALS_FILE
    ):

        try:

            with open(
                SIGNALS_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(
                    file
                )

        except Exception:
            pass

    return []


def save_signals(signals):

    content = json.dumps(
        signals,
        ensure_ascii=False,
        indent=2
    )

    with open(
        SIGNALS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(content)

    github_save_file(
        SIGNALS_FILE,
        content,
        "Actualizar señales"
    )


# ============================================================
# OFFSET
# ============================================================

def load_offset():

    content, _ = github_get_file(
        OFFSET_FILE
    )

    if content:

        try:

            data = json.loads(
                content
            )

            return data.get(
                "offset"
            )

        except Exception:
            pass

    if os.path.exists(
        OFFSET_FILE
    ):

        try:

            with open(
                OFFSET_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                data = json.load(
                    file
                )

                return data.get(
                    "offset"
                )

        except Exception:
            pass

    return None


def save_offset(offset):

    content = json.dumps(
        {
            "offset": offset
        },
        indent=2
    )

    with open(
        OFFSET_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(content)

    github_save_file(
        OFFSET_FILE,
        content,
        "Actualizar Telegram offset"
    )


# ============================================================
# MENÚ PRINCIPAL
# ============================================================

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
                "text": "⬅️ Volver",
                "callback_data": "inicio"
            }
        ]

    ]


# ============================================================
# ESTADÍSTICAS
# ============================================================

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

    effectiveness = (

        won / finished * 100

        if finished

        else 0
    )

    total_staked = finished * BET_AMOUNT

    roi = (

        profit / total_staked * 100

        if total_staked

        else 0
    )

    return {
        "total": len(signals),
        "won": won,
        "lost": lost,
        "pending": pending,
        "effectiveness": effectiveness,
        "profit": profit,
        "roi": roi
    }


# ============================================================
# PANEL
# ============================================================

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

Selecciona una sección:
"""


# ============================================================
# RENDIMIENTO
# ============================================================

def rendimiento_text():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    return f"""
📊 RENDIMIENTO
━━━━━━━━━━━━━━━━━━━━

📥 Total de señales
{stats['total']}

✅ Ganadas
{stats['won']}

❌ Perdidas
{stats['lost']}

⏳ Pendientes
{stats['pending']}

🎯 Efectividad
{stats['effectiveness']:.1f}%

📈 ROI
{stats['roi']:.1f}%

💰 Ganancia
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━

💵 Apuesta fija:
${BET_AMOUNT:,.0f} COP
"""


# ============================================================
# ESTRATEGIAS
# ============================================================

def estrategias_text():

    signals = load_signals()

    strategies = {}

    for signal in signals:

        strategy = signal.get(
            "strategy",
            "SIN ESTRATEGIA"
        )

        if strategy not in strategies:

            strategies[
                strategy
            ] = []

        strategies[
            strategy
        ].append(
            signal
        )

    if not strategies:

        return (
            "🎯 No hay estrategias registradas."
        )

    text = """
🎯 RENDIMIENTO POR ESTRATEGIA
━━━━━━━━━━━━━━━━━━━━
"""

    for strategy, items in strategies.items():

        stats = calculate_stats(
            items
        )

        text += f"""

🏷️ {strategy}

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


# ============================================================
# PENDIENTES
# ============================================================

def pendientes_text():

    signals = load_signals()

    pending = [

        s for s in signals

        if s.get(
            "result"
        ) == "PENDIENTE"

    ]

    if not pending:

        return (
            "🟢 No hay apuestas pendientes."
        )

    text = """
⏳ APUESTAS PENDIENTES
━━━━━━━━━━━━━━━━━━━━
"""

    for signal in pending:

        text += f"""

🆔 #{signal['id']}

🏆 {signal.get('league')}

⚽ {signal.get('match')}

🎯 {signal.get('strategy')}

💰 Cuota:
{signal.get('odds') or 'N/D'}

━━━━━━━━━━━━━━━━━━━━
"""

    return text


# ============================================================
# CALENDARIO
# ============================================================

def calendario_text():

    signals = load_signals()

    grouped = {}

    for signal in signals:

        date = signal.get(
            "registered_at",
            ""
        )[:10]

        if not date:
            continue

        if date not in grouped:

            grouped[date] = []

        grouped[
            date
        ].append(
            signal
        )

    if not grouped:

        return (
            "📅 No hay señales registradas."
        )

    text = """
📅 CALENDARIO
━━━━━━━━━━━━━━━━━━━━
"""

    for date in sorted(
        grouped.keys(),
        reverse=True
    ):

        items = grouped[
            date
        ]

        stats = calculate_stats(
            items
        )

        text += f"""

📆 {date}

📥 {stats['total']} señales
✅ {stats['won']} ganadas
❌ {stats['lost']} perdidas
⏳ {stats['pending']} pendientes

💰 ${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
"""

    return text


# ============================================================
# GANANCIAS
# ============================================================

def ganancias_text():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    total_finished = (
        stats["won"]
        +
        stats["lost"]
    )

    total_staked = (
        total_finished
        *
        BET_AMOUNT
    )

    return f"""
💰 GANANCIAS
━━━━━━━━━━━━━━━━━━━━

💵 Apuesta fija
${BET_AMOUNT:,.0f} COP

📥 Apuestas finalizadas
{total_finished}

💰 Resultado acumulado
${stats['profit']:,.0f} COP

📈 ROI
{stats['roi']:.1f}%

🎯 Efectividad
{stats['effectiveness']:.1f}%

💵 Capital apostado
${total_staked:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
"""


# ============================================================
# ESTADÍSTICAS
# ============================================================

def estadisticas_text():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    odds = [

        s.get("odds")

        for s in signals

        if s.get("odds")
    ]

    average_odds = (

        sum(odds)
        /
        len(odds)

        if odds

        else 0
    )

    return f"""
📈 ESTADÍSTICAS
━━━━━━━━━━━━━━━━━━━━

📥 Señales
{stats['total']}

✅ Ganadas
{stats['won']}

❌ Perdidas
{stats['lost']}

⏳ Pendientes
{stats['pending']}

🎯 Efectividad
{stats['effectiveness']:.1f}%

📈 ROI
{stats['roi']:.1f}%

💰 Ganancia
${stats['profit']:,.0f} COP

🎲 Cuota promedio
{average_odds:.2f}

━━━━━━━━━━━━━━━━━━━━
"""


# ============================================================
# CONFIGURACIÓN
# ============================================================

def configuracion_text():

    return f"""
⚙️ CONFIGURACIÓN
━━━━━━━━━━━━━━━━━━━━

💵 Apuesta fija

${BET_AMOUNT:,.0f} COP

📡 Recepción

Telegram → Bot

💾 Historial

signals.json

🔄 Control de mensajes

telegram_offset.json

━━━━━━━━━━━━━━━━━━━━

ℹ️ Esta sección muestra
la configuración actual.
"""


# ============================================================
# PROCESAR BOTONES
# ============================================================

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
            rendimiento_text(),
            back_keyboard()
        )

        return

    if data == "estrategias":

        edit_message(
            chat_id,
            message_id,
            estrategias_text(),
            back_keyboard()
        )

        return

    if data == "calendario":

        edit_message(
            chat_id,
            message_id,
            calendario_text(),
            back_keyboard()
        )

        return

    if data == "pendientes":

        edit_message(
            chat_id,
            message_id,
            pendientes_text(),
            back_keyboard()
        )

        return

    if data == "ganancias":

        edit_message(
            chat_id,
            message_id,
            ganancias_text(),
            back_keyboard()
        )

        return

    if data == "estadisticas":

        edit_message(
            chat_id,
            message_id,
            estadisticas_text(),
            back_keyboard()
        )

        return

    if data == "configuracion":

        edit_message(
            chat_id,
            message_id,
            configuracion_text(),
            back_keyboard()
        )

        return


# ============================================================
# EXTRAER DATOS
# ============================================================

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

    value = extract(
        text,
        [
            r"ESTRATEGIA\s*:\s*(.+)",
            r"RESULTADO DESEADO\s*:\s*(.+)"
        ],
        ""
    )

    if value:

        return value

    lower = text.lower()

    if "más de 3.5" in lower:

        return "Más de 3.5 goles"

    if "más de 2.5" in lower:

        return "Más de 2.5 goles"

    if (
        "ambos marcan" in lower
        or
        "btts" in lower
    ):

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
            r"CUOTA\s*:\s*([\d.,]+)",
            r"bet365\s*:\s*([\d.,]+)"
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


# ============================================================
# DETECTAR ALERTA
# ============================================================

def is_bet_alert(text):

    if not text:
        return False

    if text.startswith("/"):

        return False

    lower = text.lower()

    keywords = [

        "liga:",
        "partido:",
        "fecha:",
        "estrategia:",
        "resultado deseado:",
        "cuota:",
        "success betmines:",
        "roi betmines:",
        "picks:",
        "ranking:",
        "🏆",
        "🆚",
        "🗓"
    ]

    found = 0

    for keyword in keywords:

        if keyword in lower:

            found += 1

    return found >= 2


# ============================================================
# REGISTRAR SEÑAL
# ============================================================

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
                    r"LIGA\s*:\s*(.+)",
                    r"🏆\s*(.+)"
                ]
            ),

        "match":
            extract(
                text,
                [
                    r"PARTIDO\s*:\s*(.+)",
                    r"🆚\s*(.+)"
                ]
            ),

        "date":
            extract(
                text,
                [
                    r"FECHA\s*:\s*(.+)",
                    r"🗓\s*(.+)"
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

        "profit":
            0,

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


# ============================================================
# MENSAJES
# ============================================================

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
        text[:100]
    )

    command = text.split()[0].lower()

    if command == "/start":

        send_message(
            chat_id,
            dashboard(),
            main_keyboard()
        )

        return

    if command == "/panel":

        send_message(
            chat_id,
            dashboard(),
            main_keyboard()
        )

        return

    # Comandos antiguos también funcionan

    if command == "/estrategias":

        send_message(
            chat_id,
            estrategias_text(),
            back_keyboard()
        )

        return

    if command == "/pendientes":

        send_message(
            chat_id,
            pendientes_text(),
            back_keyboard()
        )

        return

    if command == "/calendario":

        send_message(
            chat_id,
            calendario_text(),
            back_keyboard()
        )

        return

    # Ignorar comandos desconocidos

    if text.startswith("/"):

        print(
            "Comando ignorado:",
            text
        )

        return

    # Señal

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

    odds_text = (

        f"{odds:.2f}"

        if odds

        else "N/D"
    )

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

⏳ PENDIENTE

━━━━━━━━━━━━━━━━━━━━

📊 Pulsa /panel para
ver el dashboard.
"""
    )


# ============================================================
# RECIBIR ACTUALIZACIONES
# ============================================================

def get_updates(offset=None):

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

        data = response.json()

        if not data.get(
            "ok"
        ):

            print(
                "Telegram error:",
                data
            )

            return []

        return data.get(
            "result",
            []
        )

    except Exception as e:

        print(
            "Error getUpdates:",
            e
        )

        return []


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "===================================="
    )

    print(
        "     APUESTASMURCIA BOT"
    )

    print(
        "     PANEL CON BOTONES"
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

                process_callback(
                    update["callback_query"]
                )

        except Exception as e:

            print(
                "Error procesando:",
                e
            )

        if update_id is not None:

            save_offset(
                update_id + 1
            )

    print(
        "Ejecución terminada."
    )


if __name__ == "__main__":

    main()