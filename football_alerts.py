import os
import re
import json
import base64
import requests
from datetime import datetime, timezone

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
FOOTBALL_DATA_API_KEY = os.environ.get("FOOTBALL_DATA_API_KEY", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
FOOTBALL_URL = "https://footballdata.io/api/v1"

SIGNALS_FILE = "signals.json"
OFFSET_FILE = "telegram_offset.json"

BET_AMOUNT = 5000


# ============================================================
# GITHUB
# ============================================================

def github_headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }


def github_get_file(filename):

    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        return None, None

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPOSITORY}/contents/{filename}"
    )

    try:
        r = requests.get(
            url,
            headers=github_headers(),
            timeout=30
        )

        if not r.ok:
            return None, None

        data = r.json()

        content = base64.b64decode(
            data["content"]
        ).decode("utf-8")

        return content, data.get("sha")

    except Exception as e:
        print("Error GitHub:", e)
        return None, None


def github_save_file(filename, content, message):

    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        return False

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPOSITORY}/contents/{filename}"
    )

    try:

        old_content, sha = github_get_file(
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

        r = requests.put(
            url,
            headers=github_headers(),
            json=payload,
            timeout=30
        )

        if r.ok:
            print(f"{filename} guardado.")
            return True

        print(
            "Error guardando:",
            filename,
            r.status_code,
            r.text
        )

        return False

    except Exception as e:

        print(
            "Error GitHub:",
            e
        )

        return False


# ============================================================
# SEÑALES
# ============================================================

def load_signals():

    content, _ = github_get_file(
        SIGNALS_FILE
    )

    if content:

        try:
            return json.loads(content)
        except Exception:
            pass

    if os.path.exists(SIGNALS_FILE):

        try:

            with open(
                SIGNALS_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

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
    ) as f:

        f.write(content)

    github_save_file(
        SIGNALS_FILE,
        content,
        "Actualizar señales"
    )


# ============================================================
# OFFSET TELEGRAM
# ============================================================

def load_offset():

    content, _ = github_get_file(
        OFFSET_FILE
    )

    if content:

        try:

            data = json.loads(content)

            return data.get(
                "offset"
            )

        except Exception:
            pass

    if os.path.exists(OFFSET_FILE):

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
    ) as f:

        f.write(content)

    github_save_file(
        OFFSET_FILE,
        content,
        "Actualizar offset Telegram"
    )


# ============================================================
# TELEGRAM
# ============================================================

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

        print(
            "Telegram error:",
            e
        )

        return False


def get_updates(offset=None):

    params = {
        "timeout": 5,
        "limit": 100
    }

    if offset is not None:
        params["offset"] = offset

    try:

        r = requests.get(
            f"{TELEGRAM_URL}/getUpdates",
            params=params,
            timeout=15
        )

        data = r.json()

        if not data.get("ok"):

            print(
                "Telegram:",
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
# EXTRACCION
# ============================================================

def extract(
    text,
    pattern,
    default="No identificado"
):

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
        r"Estrategia\s*:\s*(.+)",
        ""
    )

    if value:
        return value

    value = extract(
        text,
        r"Resultado\s*deseado\s*:\s*(.+)",
        ""
    )

    if value:
        return value

    low = text.lower()

    if (
        "más de 3.5" in low
        or
        "over 3.5" in low
    ):
        return "Más de 3.5 goles"

    if (
        "más de 2.5" in low
        or
        "over 2.5" in low
    ):
        return "Más de 2.5 goles"

    if (
        "ambos marcan" in low
        or
        "btts" in low
    ):
        return "Ambos Marcan"

    if (
        "victoria local" in low
        or
        "local gana" in low
    ):
        return "Victoria Local"

    if (
        "victoria visitante" in low
        or
        "visitante gana" in low
    ):
        return "Victoria Visitante"

    return "SIN ESTRATEGIA"


def extract_odds(text):

    patterns = [
        r"Cuota\s*:\s*([\d.,]+)",
        r"bet365\s*:\s*([\d.,]+)",
        r"Odds\s*:\s*([\d.,]+)"
    ]

    for pattern in patterns:

        value = extract(
            text,
            pattern,
            ""
        )

        if value:

            try:

                return float(
                    value.replace(",", ".")
                )

            except Exception:
                pass

    return None


# ============================================================
# DETECTAR SI ES UNA ALERTA
# ============================================================

def is_bet_alert(text):

    if not text:
        return False

    commands = [
        "/start",
        "/panel",
        "/hoy",
        "/semana",
        "/mes",
        "/calendario",
        "/estrategias",
        "/pendientes",
        "/ganada",
        "/perdida"
    ]

    first = text.split()[0].lower()

    if first in commands:
        return False

    alert_words = [
        "liga",
        "partido",
        "resultado deseado",
        "estrategia",
        "betmines",
        "success",
        "roi",
        "picks",
        "ranking",
        "🏆",
        "🆚",
        "🗓"
    ]

    found = sum(
        1
        for word in alert_words
        if word.lower() in text.lower()
    )

    return found >= 1


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
                r"(?:🏆\s*|LIGA\s*:\s*)(.+)"
            ),

        "match":
            extract(
                text,
                r"(?:🆚\s*|PARTIDO\s*:\s*)(.+)"
            ),

        "date":
            extract(
                text,
                r"(?:🗓\s*|FECHA\s*:\s*)(.+)"
            ),

        "strategy":
            extract_strategy(text),

        "odds":
            extract_odds(text),

        "result":
            "PENDIENTE",

        "profit":
            0,

        "final_score":
            None,

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
# PANEL
# ============================================================

def calculate_stats(signals):

    won = sum(
        1
        for s in signals
        if s.get("result") == "GANADA"
    )

    lost = sum(
        1
        for s in signals
        if s.get("result") == "PERDIDA"
    )

    pending = sum(
        1
        for s in signals
        if s.get("result") == "PENDIENTE"
    )

    finished = won + lost

    effectiveness = (
        won / finished * 100
        if finished
        else 0
    )

    profit = sum(
        s.get(
            "profit",
            0
        )
        for s in signals
    )

    return (
        len(signals),
        won,
        lost,
        pending,
        effectiveness,
        profit
    )


def panel():

    signals = load_signals()

    (
        total,
        won,
        lost,
        pending,
        effectiveness,
        profit
    ) = calculate_stats(
        signals
    )

    return f"""
╔══════════════════════════╗
║     APUESTASMURCIA       ║
║       DASHBOARD          ║
╚══════════════════════════╝

💵 APUESTA FIJA:
$5.000 COP

📥 SEÑALES: {total}

✅ GANADAS: {won}
❌ PERDIDAS: {lost}
⏳ PENDIENTES: {pending}

🎯 EFECTIVIDAD:
{effectiveness:.1f}%

💰 GANANCIA:
${profit:,.0f} COP

━━━━━━━━━━━━━━━━━━━━

📅 /hoy
📆 /semana
🗓️ /mes
📅 /calendario
🎯 /estrategias
⏳ /pendientes
"""


# ============================================================
# ESTRATEGIAS
# ============================================================

def strategies_panel():

    signals = load_signals()

    strategies = {}

    for signal in signals:

        strategy = signal.get(
            "strategy",
            "SIN ESTRATEGIA"
        )

        if strategy not in strategies:
            strategies[strategy] = []

        strategies[strategy].append(
            signal
        )

    output = """
╔══════════════════════════╗
║   🎯 ESTRATEGIAS         ║
╚══════════════════════════╝
"""

    for strategy, items in strategies.items():

        (
            total,
            won,
            lost,
            pending,
            effectiveness,
            profit
        ) = calculate_stats(
            items
        )

        output += f"""

🏷️ {strategy}

📥 Señales: {total}
✅ Ganadas: {won}
❌ Perdidas: {lost}
⏳ Pendientes: {pending}

🎯 Efectividad:
{effectiveness:.1f}%

💰 Ganancia:
${profit:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
"""

    return output


# ============================================================
# PENDIENTES
# ============================================================

def pending_panel():

    signals = load_signals()

    pending = [
        s for s in signals
        if s.get("result") == "PENDIENTE"
    ]

    if not pending:

        return (
            "🟢 No hay señales pendientes."
        )

    output = """
╔══════════════════════════╗
║    ⏳ PENDIENTES         ║
╚══════════════════════════╝
"""

    for signal in pending:

        output += f"""

🆔 #{signal['id']}

🏆 {signal['league']}

⚽ {signal['match']}

📅 {signal['date']}

🎯 {signal['strategy']}

💰 Cuota:
{signal.get('odds') or 'N/D'}

━━━━━━━━━━━━━━━━━━━━
"""

    return output


# ============================================================
# PROCESAR COMANDOS
# ============================================================

def process_message(message):

    chat_id = message[
        "chat"
    ]["id"]

    text = message.get(
        "text",
        ""
    ).strip()

    if not text:
        return

    # Nunca registrar comandos como apuestas

    if text == "/start":

        send_message(
            chat_id,
            """
🤖 APUESTASMURCIA BOT

🟢 Bot activo.

Envíame las alertas de BetMines.

📊 /panel
📅 /hoy
📆 /semana
🗓️ /mes
📅 /calendario
🎯 /estrategias
⏳ /pendientes
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

    # Otros comandos reservados

    if text.startswith("/"):
        return

    # Solo registra mensajes que parezcan
    # realmente alertas

    if not is_bet_alert(text):

        print(
            "Mensaje ignorado:",
            text[:100]
        )

        return

    signal = register_signal(
        text
    )

    odds = (
        f"{signal['odds']:.2f}"
        if signal["odds"]
        else "N/D"
    )

    send_message(
        chat_id,
        f"""
╔══════════════════════════╗
║   📥 SEÑAL REGISTRADA    ║
╚══════════════════════════╝

🆔 ID: #{signal['id']}

🏆 LIGA:
{signal['league']}

⚽ PARTIDO:
{signal['match']}

📅 FECHA:
{signal['date']}

🎯 ESTRATEGIA:
{signal['strategy']}

💰 CUOTA:
{odds}

⏳ ESTADO:
PENDIENTE

━━━━━━━━━━━━━━━━━━━━

📊 /panel
🎯 /estrategias
⏳ /pendientes
"""
    )


# ============================================================
# RECOGER MENSAJES
# ============================================================

def collect_messages():

    offset = load_offset()

    updates = get_updates(
        offset
    )

    print(
        "Mensajes encontrados:",
        len(updates)
    )

    for update in updates:

        update_id = update[
            "update_id"
        ]

        offset = update_id + 1

        if "message" in update:

            try:

                process_message(
                    update["message"]
                )

            except Exception as e:

                print(
                    "Error procesando:",
                    e
                )

        save_offset(
            offset
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "======================================"
    )

    print(
        "      APUESTASMURCIA BOT"
    )

    print(
        "======================================"
    )

    print(
        "Revisando mensajes de Telegram..."
    )

    collect_messages()

    print(
        "Ejecución terminada correctamente."
    )