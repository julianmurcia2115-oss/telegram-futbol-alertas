import os
import re
import json
import time
import requests
from datetime import datetime, timezone

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

DATA_FILE = "signals.json"


def load_signals():

    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return []


def save_signals(signals):

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            signals,
            f,
            ensure_ascii=False,
            indent=2
        )


def send_message(chat_id, text):

    try:

        r = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": text
            },
            timeout=30
        )

        return r.ok

    except Exception as e:

        print("Error Telegram:", e)

        return False


def extract(text, pattern, default="No identificado"):

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1).strip()

    return default


def extract_strategy(text):

    # Formato principal
    result = extract(
        text,
        r"Resultado\s*deseado\s*:\s*(.+)"
    )

    if result != "No identificado":
        return result

    # Respaldo para líneas con 🎯
    for line in text.splitlines():

        line = line.strip()

        if "🎯" in line and ":" in line:

            value = line.split(":", 1)[1].strip()

            if value:
                return value

    return "SIN ESTRATEGIA"


def extract_odds(text):

    value = extract(
        text,
        r"bet365:\s*([\d.,]+)",
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


def register_signal(text):

    signals = load_signals()

    strategy = extract_strategy(text)

    signal = {

        "id": len(signals) + 1,

        "registered_at":
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "league": extract(
            text,
            r"🏆\s*(.+)"
        ),

        "match": extract(
            text,
            r"🆚\s*(.+)"
        ),

        "date": extract(
            text,
            r"🗓\s*(.+)"
        ),

        "strategy": strategy,

        "odds": extract_odds(text),

        "result": "PENDIENTE",

        "raw_message": text
    }

    signals.append(signal)

    save_signals(signals)

    return signal


def format_signal(signal):

    odds = signal["odds"]

    if odds is None:
        odds_text = "N/D"
    else:
        odds_text = f"{odds:.2f}"

    return f"""
SEÑAL REGISTRADA

ID: #{signal['id']}

LIGA:
{signal['league']}

PARTIDO:
{signal['match']}

FECHA:
{signal['date']}

ESTRATEGIA:
{signal['strategy']}

CUOTA:
{odds_text}

ESTADO:
PENDIENTE

Comandos:

/panel
/estrategias
/pendientes
"""


def panel():

    signals = load_signals()

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

    if finished:

        effectiveness = (
            won / finished
        ) * 100

    else:

        effectiveness = 0

    profit = 0

    for s in signals:

        odds = s.get("odds")

        if s["result"] == "GANADA":

            if odds:
                profit += 5000 * (odds - 1)
            else:
                profit += 5000

        elif s["result"] == "PERDIDA":

            profit -= 5000

    return f"""
==============================
      APUESTASMURCIA
        DASHBOARD
==============================

APUESTA FIJA:
$5.000 COP

SEÑALES: {total}

GANADAS: {won}
PERDIDAS: {lost}
PENDIENTES: {pending}

EFECTIVIDAD:
{effectiveness:.1f}%

GANANCIA:
${profit:,.0f} COP

==============================
"""


def strategies_panel():

    signals = load_signals()

    strategies = {}

    for s in signals:

        strategy = s.get(
            "strategy",
            "SIN ESTRATEGIA"
        )

        if strategy not in strategies:

            strategies[strategy] = {
                "total": 0,
                "won": 0,
                "lost": 0,
                "pending": 0,
                "profit": 0
            }

        data = strategies[strategy]

        data["total"] += 1

        odds = s.get("odds")

        if s["result"] == "GANADA":

            data["won"] += 1

            if odds:
                data["profit"] += (
                    5000 * (odds - 1)
                )
            else:
                data["profit"] += 5000

        elif s["result"] == "PERDIDA":

            data["lost"] += 1

            data["profit"] -= 5000

        else:

            data["pending"] += 1

    output = """
==============================
   RENDIMIENTO POR ESTRATEGIA
==============================
"""

    for strategy, data in strategies.items():

        finished = (
            data["won"]
            + data["lost"]
        )

        if finished:

            effectiveness = (
                data["won"]
                / finished
            ) * 100

        else:

            effectiveness = 0

        output += f"""

ESTRATEGIA:
{strategy}

SEÑALES: {data['total']}

GANADAS: {data['won']}
PERDIDAS: {data['lost']}
PENDIENTES: {data['pending']}

EFECTIVIDAD:
{effectiveness:.1f}%

GANANCIA:
${data['profit']:,.0f} COP

------------------------------
"""

    return output


def pending_panel():

    signals = load_signals()

    pending = [

        s for s in signals
        if s["result"] == "PENDIENTE"

    ]

    if not pending:

        return "No hay señales pendientes."

    output = """
==============================
      SEÑALES PENDIENTES
==============================
"""

    for s in pending:

        output += f"""

#{s['id']}
{s['match']}

Estrategia:
{s['strategy']}

Cuota:
{s.get('odds') or 'N/D'}

------------------------------
"""

    return output


def update_result(signal_id, result):

    signals = load_signals()

    for s in signals:

        if s["id"] == signal_id:

            s["result"] = result

            save_signals(signals)

            return True

    return False


def process_message(message):

    chat_id = message["chat"]["id"]

    text = message.get(
        "text",
        ""
    ).strip()

    if not text:
        return

    if text == "/start":

        send_message(
            chat_id,
            """
APUESTASMURCIA BOT

Estoy activo.

Envíame cualquier alerta
de BetMines.

Comandos:

/panel
/estrategias
/pendientes

Para resultados:

/ganada ID
/perdida ID
"""
        )

        return

    if text == "/panel":

        send_message(
            chat_id,
            panel()
        )

        return

    if text == "/estrategias":

        send_message(
            chat_id,
            strategies_panel()
        )

        return

    if text == "/pendientes":

        send_message(
            chat_id,
            pending_panel()
        )

        return

    match = re.match(
        r"^/ganada\s+(\d+)$",
        text
    )

    if match:

        signal_id = int(
            match.group(1)
        )

        if update_result(
            signal_id,
            "GANADA"
        ):

            send_message(
                chat_id,
                f"Señal #{signal_id} marcada como GANADA."
            )

        else:

            send_message(
                chat_id,
                "No existe esa señal."
            )

        return

    match = re.match(
        r"^/perdida\s+(\d+)$",
        text
    )

    if match:

        signal_id = int(
            match.group(1)
        )

        if update_result(
            signal_id,
            "PERDIDA"
        ):

            send_message(
                chat_id,
                f"Señal #{signal_id} marcada como PERDIDA."
            )

        else:

            send_message(
                chat_id,
                "No existe esa señal."
            )

        return

    signal = register_signal(text)

    send_message(
        chat_id,
        format_signal(signal)
    )


def run_bot():

    print("======================================")
    print("      APUESTASMURCIA BOT")
    print("======================================")
    print("Bot iniciado.")
    print("Esperando alertas de BetMines...")
    print("======================================")

    offset = None

    while True:

        try:

            params = {
                "timeout": 30
            }

            if offset is not None:

                params["offset"] = offset

            r = requests.get(
                f"{TELEGRAM_URL}/getUpdates",
                params=params,
                timeout=40
            )

            data = r.json()

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
                "Error:",
                e
            )

            time.sleep(5)


if __name__ == "__main__":

    run_bot()