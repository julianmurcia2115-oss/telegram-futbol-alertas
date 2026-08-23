import os
import re
import json
import time
import requests
from datetime import datetime, timezone

# ============================================================
# CONFIGURACIÓN
# ============================================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

DATA_FILE = "signals.json"

# ============================================================
# BASE DE DATOS SIMPLE
# ============================================================

def load_signals():

    if not os.path.exists(DATA_FILE):
        return []

    try:

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:

        return []


def save_signals(signals):

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            signals,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# TELEGRAM
# ============================================================

def send_message(chat_id, message):

    try:

        r = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": message
            },
            timeout=30
        )

        return r.ok

    except Exception as e:

        print("Error Telegram:", e)

        return False


# ============================================================
# EXTRAER DATOS DE LA ALERTA
# ============================================================

def extract_probability(text):

    patterns = [
        r'probabilidad\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%',
        r'probability\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*%'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return float(match.group(1))

    return None


def extract_odds(text):

    patterns = [
        r'cuota\s*[:\-]?\s*(\d+(?:[.,]\d+)?)',
        r'odd\s*[:\-]?\s*(\d+(?:[.,]\d+)?)',
        r'odds\s*[:\-]?\s*(\d+(?:[.,]\d+)?)'
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return float(
                match.group(1).replace(",", ".")
            )

    return None


def detect_strategy(text):

    text_lower = text.lower()

    if (
        "ambos marcan" in text_lower
        or "btts" in text_lower
        or "both teams to score" in text_lower
    ):
        return "BTTS"

    if (
        "más de 2.5" in text_lower
        or "over 2.5" in text_lower
        or "over2.5" in text_lower
    ):
        return "OVER 2.5"

    if (
        "empate 1t" in text_lower
        or "empate 1er tiempo" in text_lower
        or "half time draw" in text_lower
        or "ht draw" in text_lower
    ):
        return "EMPATE 1T"

    return "OTRA"


def extract_match(text):

    # Intenta detectar:
    # Equipo A vs Equipo B
    # Equipo A - Equipo B
    # Equipo A v Equipo B

    patterns = [
        r'(.+?)\s+vs\.?\s+(.+)',
        r'(.+?)\s+-\s+(.+)',
        r'(.+?)\s+v\s+(.+)'
    ]

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for line in lines:

        match = None

        for pattern in patterns:

            match = re.search(
                pattern,
                line,
                re.IGNORECASE
            )

            if match:
                break

        if not match:
            continue

        home = match.group(1).strip()
        away = match.group(2).strip()

        # Evitar detectar frases que no sean partidos
        if len(home) > 2 and len(away) > 2:

            return f"{home} vs {away}"

    return "No identificado"


# ============================================================
# REGISTRAR ALERTA
# ============================================================

def register_signal(text):

    signals = load_signals()

    strategy = detect_strategy(text)
    probability = extract_probability(text)
    odds = extract_odds(text)
    match = extract_match(text)

    signal = {

        "id": len(signals) + 1,

        "date": datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M:%S"),

        "match": match,

        "strategy": strategy,

        "probability": probability,

        "odds": odds,

        "result": "PENDIENTE",

        "raw_message": text
    }

    signals.append(signal)

    save_signals(signals)

    return signal


# ============================================================
# PANEL
# ============================================================

def panel():

    signals = load_signals()

    if not signals:

        return (
            "📊 PANEL\n\n"
            "Todavía no hay señales registradas."
        )

    total = len(signals)

    won = sum(
        1
        for s in signals
        if s["result"] == "GANADA"
    )

    lost = sum(
        1
        for s in signals
        if s["result"] == "PERDIDA"
    )

    pending = sum(
        1
        for s in signals
        if s["result"] == "PENDIENTE"
    )

    finished = won + lost

    if finished > 0:

        effectiveness = (
            won / finished
        ) * 100

    else:

        effectiveness = 0

    # ROI sencillo con stake de 1 unidad

    profit = 0

    for signal in signals:

        if signal["result"] == "GANADA":

            odds = signal.get("odds")

            if odds:
                profit += odds - 1
            else:
                profit += 1

        elif signal["result"] == "PERDIDA":

            profit -= 1

    if total > 0:

        roi = (
            profit / total
        ) * 100

    else:

        roi = 0

    return f"""
📊 PANEL DE RENDIMIENTO

━━━━━━━━━━━━━━━━

📥 Total señales: {total}

✅ Ganadas: {won}
❌ Perdidas: {lost}
⏳ Pendientes: {pending}

🎯 Efectividad:
{effectiveness:.1f}%

💰 Beneficio:
{profit:+.2f} unidades

📈 ROI:
{roi:+.1f}%

━━━━━━━━━━━━━━━━

🤖 Apuestasmurcia Bot
"""


# ============================================================
# RENDIMIENTO POR ESTRATEGIA
# ============================================================

def strategies_panel():

    signals = load_signals()

    if not signals:

        return "📊 No hay señales registradas."

    strategies = {}

    for signal in signals:

        strategy = signal["strategy"]

        if strategy not in strategies:

            strategies[strategy] = {
                "total": 0,
                "won": 0,
                "lost": 0
            }

        strategies[strategy]["total"] += 1

        if signal["result"] == "GANADA":
            strategies[strategy]["won"] += 1

        elif signal["result"] == "PERDIDA":
            strategies[strategy]["lost"] += 1

    message = "🎯 RENDIMIENTO POR ESTRATEGIA\n\n"

    for strategy, data in strategies.items():

        finished = (
            data["won"]
            + data["lost"]
        )

        if finished:

            pct = (
                data["won"]
                / finished
            ) * 100

        else:

            pct = 0

        message += (
            f"🏷️ {strategy}\n"
            f"📥 Señales: {data['total']}\n"
            f"✅ {data['won']} "
            f"❌ {data['lost']}\n"
            f"🎯 Efectividad: {pct:.1f}%\n\n"
        )

    return message


# ============================================================
# SEÑALES PENDIENTES
# ============================================================

def pending_panel():

    signals = load_signals()

    pending = [
        s
        for s in signals
        if s["result"] == "PENDIENTE"
    ]

    if not pending:

        return "⏳ No hay señales pendientes."

    message = "⏳ SEÑALES PENDIENTES\n\n"

    for signal in pending[-20:]:

        probability = signal["probability"]

        if probability is not None:
            probability_text = f"{probability:.1f}%"
        else:
            probability_text = "N/D"

        message += (
            f"#{signal['id']} "
            f"{signal['match']}\n"
            f"🎯 {signal['strategy']}\n"
            f"📊 {probability_text}\n"
            f"💰 {signal['odds'] or 'N/D'}\n\n"
        )

    return message


# ============================================================
# RESULTADO
# ============================================================

def update_result(signal_id, result):

    signals = load_signals()

    for signal in signals:

        if signal["id"] == signal_id:

            signal["result"] = result

            save_signals(signals)

            return signal

    return None


# ============================================================
# PROCESAR MENSAJES
# ============================================================

def process_message(message):

    chat = message.get("chat", {})

    chat_id = chat.get("id")

    text = message.get(
        "text",
        ""
    ).strip()

    if not text:
        return

    # --------------------------
    # /start
    # --------------------------

    if text == "/start":

        send_message(
            chat_id,
            """
🤖 APUESTASMURCIA BOT

Estoy funcionando.

📥 Envíame una alerta de BetMines
copiando y pegando el mensaje.

Comandos:

/panel
/hoy
/estrategias
/pendientes

Para actualizar resultados:

/ganada ID
/perdida ID
"""
        )

        return

    # --------------------------
    # /panel
    # --------------------------

    if text == "/panel":

        send_message(
            chat_id,
            panel()
        )

        return

    # --------------------------
    # /estrategias
    # --------------------------

    if text == "/estrategias":

        send_message(
            chat_id,
            strategies_panel()
        )

        return

    # --------------------------
    # /pendientes
    # --------------------------

    if text == "/pendientes":

        send_message(
            chat_id,
            pending_panel()
        )

        return

    # --------------------------
    # /hoy
    # --------------------------

    if text == "/hoy":

        today = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")

        signals = load_signals()

        today_signals = [
            s
            for s in signals
            if s["date"].startswith(today)
        ]

        if not today_signals:

            send_message(
                chat_id,
                "📅 No hay señales registradas hoy."
            )

            return

        message_out = "📅 SEÑALES DE HOY\n\n"

        for signal in today_signals:

            message_out += (
                f"#{signal['id']} "
                f"{signal['match']}\n"
                f"🎯 {signal['strategy']}\n"
                f"📊 {signal['probability'] or 'N/D'}%\n"
                f"💰 {signal['odds'] or 'N/D'}\n"
                f"📌 {signal['result']}\n\n"
            )

        send_message(
            chat_id,
            message_out
        )

        return

    # --------------------------
    # /ganada
    # --------------------------

    match = re.match(
        r'^/ganada\s+(\d+)$',
        text
    )

    if match:

        signal_id = int(
            match.group(1)
        )

        signal = update_result(
            signal_id,
            "GANADA"
        )

        if signal:

            send_message(
                chat_id,
                f"✅ Señal #{signal_id} marcada como GANADA."
            )

        else:

            send_message(
                chat_id,
                "❌ No encontré esa señal."
            )

        return

    # --------------------------
    # /perdida
    # --------------------------

    match = re.match(
        r'^/perdida\s+(\d+)$',
        text
    )

    if match:

        signal_id = int(
            match.group(1)
        )

        signal = update_result(
            signal_id,
            "PERDIDA"
        )

        if signal:

            send_message(
                chat_id,
                f"❌ Señal #{signal_id} marcada como PERDIDA."
            )

        else:

            send_message(
                chat_id,
                "❌ No encontré esa señal."
            )

        return

    # ========================================================
    # SI NO ES COMANDO → ES UNA ALERTA DE BETMINES
    # ========================================================

    signal = register_signal(text)

    probability = signal["probability"]

    if probability is not None:

        probability_text = (
            f"{probability:.1f}%"
        )

    else:

        probability_text = "No detectada"

    odds = signal["odds"]

    if odds is not None:

        odds_text = f"{odds:.2f}"

    else:

        odds_text = "No detectada"

    response = f"""
📥 SEÑAL REGISTRADA

🆔 #{signal['id']}

⚽ {signal['match']}

🎯 Estrategia:
{signal['strategy']}

📊 Probabilidad:
{probability_text}

💰 Cuota:
{odds_text}

⏳ Estado:
PENDIENTE

━━━━━━━━━━━━━━━━

Puedes consultar:

/panel
/estrategias
/pendientes
"""

    send_message(
        chat_id,
        response
    )


# ============================================================
# TELEGRAM LONG POLLING
# ============================================================

def run_bot():

    print("")
    print("======================================")
    print("      APUESTASMURCIA BOT")
    print("======================================")
    print("Bot iniciado.")
    print("Esperando señales...")
    print("======================================")

    offset = None

    while True:

        try:

            params = {
                "timeout": 30
            }

            if offset is not None:

                params["offset"] = offset

            response = requests.get(
                f"{TELEGRAM_URL}/getUpdates",
                params=params,
                timeout=40
            )

            data = response.json()

            if not data.get("ok"):

                print(
                    "Error Telegram:",
                    data
                )

                time.sleep(5)

                continue

            for update in data.get(
                "result",
                []
            ):

                offset = (
                    update["update_id"] + 1
                )

                if "message" in update:

                    process_message(
                        update["message"]
                    )

        except Exception as e:

            print(
                "Error en polling:",
                e
            )

            time.sleep(5)


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":

    run_bot()