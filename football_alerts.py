import os
import re
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# =========================================================
# CONFIGURACIÓN
# =========================================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API_FOOTBALL_KEY = os.environ.get("API_FOOTBALL_KEY", "")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
FOOTBALL_API_URL = "https://v3.football.api-sports.io"

SIGNALS_FILE = "signals.json"
OFFSET_FILE = "telegram_offset.json"

BET_AMOUNT = 5000

# 🇨🇴 HORA OFICIAL DE COLOMBIA
COLOMBIA_TZ = ZoneInfo("America/Bogota")


# =========================================================
# HORA COLOMBIA
# =========================================================

def colombia_now():
    return datetime.now(COLOMBIA_TZ)


def colombia_date():
    return colombia_now().strftime("%Y-%m-%d")


def colombia_datetime():
    return colombia_now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


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
            f"{result.get('ok')}"
        )

        if not result.get("ok"):
            print("Telegram:", result)

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

    if not os.path.exists(SIGNALS_FILE):
        return []

    try:

        with open(
            SIGNALS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

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
        ) as file:

            json.dump(
                signals,
                file,
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

    if not os.path.exists(OFFSET_FILE):
        return None

    try:

        with open(
            OFFSET_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        return data.get("offset")

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
        ) as file:

            json.dump(
                {
                    "offset": offset
                },
                file,
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


def calendar_keyboard():

    return [

        [
            {
                "text": "📆 Hoy",
                "callback_data": "cal_hoy"
            },
            {
                "text": "📆 7 días",
                "callback_data": "cal_semana"
            }
        ],

        [
            {
                "text": "🗓️ Este mes",
                "callback_data": "cal_mes"
            },
            {
                "text": "📚 Todo",
                "callback_data": "cal_todo"
            }
        ],

        [
            {
                "text": "⬅️ Volver",
                "callback_data": "inicio"
            }
        ]

    ]


# =========================================================
# EXTRACCIÓN
# =========================================================

def extract(
    text,
    patterns,
    default="No identificado"
):

    if isinstance(patterns, str):
        patterns = [patterns]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(1).strip()

    return default


def extract_strategy(text):

    result = extract(
        text,
        [
            r"Resultado\s*deseado\s*:\s*(.+)",
            r"Estrategia\s*:\s*(.+)"
        ],
        ""
    )

    if result:
        return result

    lower = text.lower()

    if (
        "empate" in lower
        and (
            "primer tiempo" in lower
            or "1er tiempo" in lower
        )
    ):
        return "Empate Primer Tiempo"

    if (
        "más de 3.5" in lower
        or "over 3.5" in lower
    ):
        return "Más de 3.5 goles"

    if (
        "más de 2.5" in lower
        or "over 2.5" in lower
    ):
        return "Más de 2.5 goles"

    if (
        "ambos marcan" in lower
        or "btts" in lower
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
            r"bet365\s*:\s*([\d.,]+)",
            r"cuota\s*:\s*([\d.,]+)"
        ],
        ""
    )

    if not value:
        return None

    try:

        return float(
            value.replace(",", ".")
        )

    except Exception:

        return None


def extract_signal_date(text):

    value = extract(
        text,
        [
            r"🗓\s*(.+)",
            r"Fecha\s*:\s*(.+)"
        ],
        ""
    )

    if not value:
        return None

    patterns = [
        r"(\d{4})-(\d{2})-(\d{2})",
        r"(\d{2})/(\d{2})/(\d{4})",
        r"(\d{2})-(\d{2})-(\d{4})"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            value
        )

        if not match:
            continue

        groups = match.groups()

        try:

            if len(groups[0]) == 4:

                year, month, day = groups

            else:

                day, month, year = groups

            return (
                f"{year}-"
                f"{month.zfill(2)}-"
                f"{day.zfill(2)}"
            )

        except Exception:
            pass

    lower = value.lower()

    if "mañana" in lower:

        return (
            colombia_now()
            + timedelta(days=1)
        ).strftime("%Y-%m-%d")

    if "hoy" in lower:

        return colombia_date()

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
        "over 2.5",
        "over 3.5",
        "ambos marcan",
        "victoria local",
        "victoria visitante",
        "empate"

    ]

    matches = 0

    for keyword in keywords:

        if keyword.lower() in lower:
            matches += 1

    return matches >= 2


# =========================================================
# REGISTRAR SEÑAL
# =========================================================

def next_signal_id(signals):

    if not signals:
        return 1

    ids = []

    for signal in signals:

        try:

            ids.append(
                int(
                    signal.get(
                        "id",
                        0
                    )
                )
            )

        except Exception:
            pass

    if not ids:
        return 1

    return max(ids) + 1


def signal_already_exists(
    text,
    signals
):

    clean_text = text.strip()

    for signal in signals:

        old_text = signal.get(
            "raw_message",
            ""
        ).strip()

        if old_text == clean_text:
            return True

    return False


def register_signal(text):

    signals = load_signals()

    if signal_already_exists(
        text,
        signals
    ):

        print(
            "Señal duplicada."
        )

        return None

    signal = {

        "id":
            next_signal_id(
                signals
            ),

        "registered_at":
            colombia_datetime(),

        "timezone":
            "America/Bogota",

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

        "api_date":
            extract_signal_date(
                text
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

        "result_at":
            None,

        "fixture_id":
            None,

        "raw_message":
            text
    }

    signals.append(signal)

    save_signals(signals)

    return signal


# =========================================================
# ESTADÍSTICAS
# =========================================================

def calculate_stats(signals):

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

            if (
                isinstance(
                    odds,
                    (int, float)
                )
                and odds > 1
            ):

                profit += (
                    BET_AMOUNT *
                    (odds - 1)
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

    total_staked = (
        finished *
        BET_AMOUNT
    )

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


# =========================================================
# PANEL
# =========================================================

def dashboard():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    now = colombia_now()

    return f"""
🏆 APUESTASMURCIA
━━━━━━━━━━━━━━━━━━━━

🇨🇴 HORA COLOMBIA
{now.strftime("%d/%m/%Y %H:%M")}

🎛️ CENTRO DE CONTROL

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

💰 Resultado
${stats['profit']:,.0f} COP

💵 Apuesta
${BET_AMOUNT:,.0f} COP

━━━━━━━━━━━━━━━━━━━━

👇 Selecciona una opción
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

📥 Señales
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

💰 Resultado
${stats['profit']:,.0f} COP
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

        groups.setdefault(
            strategy,
            []
        ).append(signal)

    if not groups:

        return (
            "🎯 No hay estrategias registradas."
        )

    text = """
🎯 ESTRATEGIAS
━━━━━━━━━━━━━━━━━━━━
"""

    for strategy, items in sorted(
        groups.items()
    ):

        stats = calculate_stats(
            items
        )

        text += f"""

🎯 {strategy}

📥 {stats['total']} señales
✅ {stats['won']} ganadas
❌ {stats['lost']} perdidas
⏳ {stats['pending']} pendientes

🎯 Efectividad:
{stats['effectiveness']:.1f}%

📈 ROI:
{stats['roi']:.1f}%

💰 Resultado:
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

        return (
            "⏳ PENDIENTES\n\n"
            "🟢 No tienes señales pendientes."
        )

    text = """
⏳ SEÑALES PENDIENTES
━━━━━━━━━━━━━━━━━━━━
"""

    for signal in pending[:25]:

        odds = signal.get(
            "odds"
        )

        odds_text = (

            f"{odds:.2f}"

            if isinstance(
                odds,
                (int, float)
            )

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

    return text


# =========================================================
# CALENDARIO
# =========================================================

def signal_colombia_date(signal):

    value = signal.get(
        "registered_at",
        ""
    )

    try:

        dt = datetime.strptime(
            value,
            "%Y-%m-%d %H:%M:%S"
        )

        return dt.date()

    except Exception:

        return None


def calendario(period="todo"):

    signals = load_signals()

    now = colombia_now()

    today = now.date()

    if period == "hoy":

        start = today

    elif period == "semana":

        start = today - timedelta(
            days=6
        )

    elif period == "mes":

        start = today.replace(
            day=1
        )

    else:

        start = None

    selected = []

    for signal in signals:

        date_value = signal_colombia_date(
            signal
        )

        if not date_value:
            continue

        if (
            start is None
            or date_value >= start
        ):

            selected.append(
                signal
            )

    stats = calculate_stats(
        selected
    )

    title = {

        "hoy":
            "📆 HOY",

        "semana":
            "📆 ÚLTIMOS 7 DÍAS",

        "mes":
            "🗓️ ESTE MES",

        "todo":
            "📚 TODO EL HISTORIAL"

    }.get(
        period,
        "📅 CALENDARIO"
    )

    return f"""
{title}
━━━━━━━━━━━━━━━━━━━━

🇨🇴 Fecha Colombia:
{today.strftime("%d/%m/%Y")}

📥 Señales
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

💰 Resultado
${stats['profit']:,.0f} COP
"""


# =========================================================
# GANANCIAS
# =========================================================

def ganancias():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    finished = (
        stats["won"] +
        stats["lost"]
    )

    invested = (
        finished *
        BET_AMOUNT
    )

    return f"""
💰 GANANCIAS
━━━━━━━━━━━━━━━━━━━━

💵 Apuesta fija
${BET_AMOUNT:,.0f} COP

📊 Finalizadas
{finished}

💸 Capital apostado
${invested:,.0f} COP

━━━━━━━━━━━━━━━━━━━━

💰 Resultado
${stats['profit']:,.0f} COP

📈 ROI
{stats['roi']:.1f}%

🎯 Efectividad
{stats['effectiveness']:.1f}%
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

            odds.append(value)

    average_odds = (

        sum(odds) / len(odds)

        if odds

        else 0

    )

    return f"""
📈 ESTADÍSTICAS
━━━━━━━━━━━━━━━━━━━━

📥 Total
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

💰 Resultado
${stats['profit']:,.0f} COP
"""


# =========================================================
# CONFIGURACIÓN
# =========================================================

def configuracion():

    api = (
        "🟢 CONFIGURADA"
        if API_FOOTBALL_KEY
        else "🔴 NO CONFIGURADA"
    )

    return f"""
⚙️ CONFIGURACIÓN
━━━━━━━━━━━━━━━━━━━━

🇨🇴 Zona horaria
America/Bogota

💵 Apuesta fija
${BET_AMOUNT:,.0f} COP

📥 Señales
Telegram / BetMines

🤖 API-Football
{api}

🔄 Ejecución
Cada 5 minutos

💾 Registro
signals.json

🔢 Offset
telegram_offset.json

━━━━━━━━━━━━━━━━━━━━
"""


# =========================================================
# CALLBACKS
# =========================================================

def process_callback(callback):

    callback_id = callback.get("id")

    data = callback.get(
        "data",
        ""
    )

    message = callback.get(
        "message"
    )

    if not message:
        return

    chat_id = message["chat"]["id"]

    message_id = message["message_id"]

    answer_callback(
        callback_id
    )

    # PANEL

    if data == "inicio":

        edit_message(
            chat_id,
            message_id,
            dashboard(),
            main_keyboard()
        )

        return

    # RENDIMIENTO

    if data == "rendimiento":

        edit_message(
            chat_id,
            message_id,
            rendimiento(),
            back_keyboard()
        )

        return

    # ESTRATEGIAS

    if data == "estrategias":

        edit_message(
            chat_id,
            message_id,
            estrategias(),
            back_keyboard()
        )

        return

    # CALENDARIO

    if data == "calendario":

        edit_message(
            chat_id,
            message_id,
            "📅 CALENDARIO\n\n"
            "🇨🇴 Selecciona el período:",
            calendar_keyboard()
        )

        return

    if data == "cal_hoy":

        edit_message(
            chat_id,
            message_id,
            calendario("hoy"),
            calendar_keyboard()
        )

        return

    if data == "cal_semana":

        edit_message(
            chat_id,
            message_id,
            calendario("semana"),
            calendar_keyboard()
        )

        return

    if data == "cal_mes":

        edit_message(
            chat_id,
            message_id,
            calendario("mes"),
            calendar_keyboard()
        )

        return

    if data == "cal_todo":

        edit_message(
            chat_id,
            message_id,
            calendario("todo"),
            calendar_keyboard()
        )

        return

    # PENDIENTES

    if data == "pendientes":

        edit_message(
            chat_id,
            message_id,
            pendientes(),
            back_keyboard()
        )

        return

    # GANANCIAS

    if data == "ganancias":

        edit_message(
            chat_id,
            message_id,
            ganancias(),
            back_keyboard()
        )

        return

    # ESTADÍSTICAS

    if data == "estadisticas":

        edit_message(
            chat_id,
            message_id,
            estadisticas(),
            back_keyboard()
        )

        return

    # CONFIGURACIÓN

    if data == "configuracion":

        edit_message(
            chat_id,
            message_id,
            configuracion(),
            back_keyboard()
        )

        return


# =========================================================
# MENSAJES
# =========================================================

def process_message(message):

    chat = message.get(
        "chat",
        {}
    )

    chat_id = chat.get("id")

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
        text[:150]
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

        send_message(
            chat_id,
            dashboard(),
            main_keyboard()
        )

        return

    # ESTRATEGIAS

    if command == "/estrategias":

        send_message(
            chat_id,
            estrategias(),
            back_keyboard()
        )

        return

    # PENDIENTES

    if command == "/pendientes":

        send_message(
            chat_id,
            pendientes(),
            back_keyboard()
        )

        return

    # CALENDARIO

    if command == "/calendario":

        send_message(
            chat_id,
            "📅 CALENDARIO\n\n"
            "🇨🇴 Selecciona el período:",
            calendar_keyboard()
        )

        return

    # COMANDO DESCONOCIDO

    if text.startswith("/"):

        print(
            "Comando ignorado:",
            text
        )

        return

    # SEÑAL

    if not is_bet_alert(text):

        print(
            "Mensaje ignorado:",
            text[:100]
        )

        return

    signal = register_signal(
        text
    )

    if signal is None:
        return

    odds = signal.get(
        "odds"
    )

    odds_text = (

        f"{odds:.2f}"

        if isinstance(
            odds,
            (int, float)
        )

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

⏳ ESTADO: PENDIENTE

🇨🇴 Registrada:
{signal['registered_at']}

━━━━━━━━━━━━━━━━━━━━

🤖 El resultado será
comprobado automáticamente.
"""
    )


# =========================================================
# TELEGRAM
# =========================================================

def get_updates(offset=None):

    params = {
        "timeout": 5,
        "limit": 100
    }

    if offset is not None:

        params["offset"] = offset

    try:

        response = requests.get(
            f"{TELEGRAM_URL}/getUpdates",
            params=params,
            timeout=15
        )

        result = response.json()

        if not result.get("ok"):

            print(
                "Error getUpdates:",
                result
            )

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
        "      APUESTASMURCIA BOT"
    )

    print(
        "      🇨🇴 HORA COLOMBIA"
    )

    print(
        "      PANEL + SEÑALES"
    )

    print(
        "===================================="
    )

    print(
        "Hora Colombia:",
        colombia_datetime()
    )

    # -----------------------------------------------------
    # Telegram
    # -----------------------------------------------------

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

        # IMPORTANTE
        # Guardar offset después
        # de procesar el update.

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
        "====================================")


if __name__ == "__main__":
    main()