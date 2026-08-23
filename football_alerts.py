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
        response = requests.get(
            url,
            headers=github_headers(),
            timeout=30
        )

        if not response.ok:
            print(
                "GitHub GET error:",
                response.status_code
            )
            return None, None

        data = response.json()

        content = base64.b64decode(
            data["content"]
        ).decode("utf-8")

        return content, data.get("sha")

    except Exception as e:

        print(
            "Error leyendo GitHub:",
            e
        )

        return None, None


def github_save_file(
    filename,
    content,
    message
):

    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
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
                f"{filename} actualizado."
            )

            return True

        print(
            "Error GitHub:",
            response.status_code,
            response.text
        )

        return False

    except Exception as e:

        print(
            "Error guardando GitHub:",
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

    if os.path.exists(
        SIGNALS_FILE
    ):

        try:

            with open(
                SIGNALS_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

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
# OFFSET TELEGRAM
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
# TELEGRAM
# ============================================================

def send_message(
    chat_id,
    text
):

    try:

        response = requests.post(
            f"{TELEGRAM_URL}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": text
            },
            timeout=30
        )

        print(
            "Telegram respuesta:",
            response.status_code
        )

        if not response.ok:

            print(
                response.text
            )

        return response.ok

    except Exception as e:

        print(
            "Error enviando Telegram:",
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
                "Error Telegram:",
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
# EXTRACCIÓN
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

    strategy = extract(
        text,
        [
            r"ESTRATEGIA\s*:\s*(.+)",
            r"Estrategia\s*:\s*(.+)",
            r"RESULTADO DESEADO\s*:\s*(.+)",
            r"Resultado deseado\s*:\s*(.+)"
        ],
        ""
    )

    if strategy:
        return strategy

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
            r"Cuota\s*:\s*([\d.,]+)",
            r"bet365\s*:\s*([\d.,]+)",
            r"ODDS\s*:\s*([\d.,]+)"
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
# DETECTAR SEÑAL
# ============================================================

def is_bet_alert(text):

    if not text:
        return False

    clean = text.strip()

    # Nunca tratar comandos como señales
    if clean.startswith("/"):
        return False

    lower = clean.lower()

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

    matches = 0

    for keyword in keywords:

        if keyword in lower:
            matches += 1

    return matches >= 2


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

        if result == "GANADA":

            won += 1

            odds = signal.get(
                "odds"
            )

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

    return (
        len(signals),
        won,
        lost,
        pending,
        effectiveness,
        profit
    )


# ============================================================
# PANEL GENERAL
# ============================================================

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
╔════════════════════════════╗
║     APUESTASMURCIA         ║
║        DASHBOARD           ║
╚════════════════════════════╝

💵 APUESTA FIJA
$5.000 COP

📥 SEÑALES
{total}

✅ GANADAS
{won}

❌ PERDIDAS
{lost}

⏳ PENDIENTES
{pending}

🎯 EFECTIVIDAD
{effectiveness:.1f}%

💰 GANANCIA
${profit:,.0f} COP

━━━━━━━━━━━━━━━━━━━━

📅 /hoy
📆 /semana
🗓 /mes
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

    output = """
╔════════════════════════════╗
║    🎯 POR ESTRATEGIA       ║
╚════════════════════════════╝
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

        signal

        for signal in signals

        if signal.get(
            "result"
        ) == "PENDIENTE"
    ]

    if not pending:

        return (
            "🟢 No hay señales pendientes."
        )

    output = """
╔════════════════════════════╗
║       ⏳ PENDIENTES         ║
╚════════════════════════════╝
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
# HOY
# ============================================================

def today_panel():

    signals = load_signals()

    today = datetime.now(
        timezone.utc
    ).date()

    today_signals = []

    for signal in signals:

        registered = signal.get(
            "registered_at",
            ""
        )

        try:

            date = datetime.strptime(
                registered,
                "%Y-%m-%d %H:%M:%S"
            ).date()

            if date == today:

                today_signals.append(
                    signal
                )

        except Exception:

            pass

    if not today_signals:

        return (
            "📅 Hoy no hay señales registradas."
        )

    (
        total,
        won,
        lost,
        pending,
        effectiveness,
        profit
    ) = calculate_stats(
        today_signals
    )

    return f"""
📅 RENDIMIENTO DE HOY

📥 Señales: {total}

✅ Ganadas: {won}
❌ Perdidas: {lost}
⏳ Pendientes: {pending}

🎯 Efectividad:
{effectiveness:.1f}%

💰 Ganancia:
${profit:,.0f} COP
"""


# ============================================================
# SEMANA
# ============================================================

def week_panel():

    signals = load_signals()

    now = datetime.now(
        timezone.utc
    )

    start = now - timedelta(
        days=7
    )

    selected = []

    for signal in signals:

        try:

            registered = datetime.strptime(
                signal["registered_at"],
                "%Y-%m-%d %H:%M:%S"
            ).replace(
                tzinfo=timezone.utc
            )

            if registered >= start:

                selected.append(
                    signal
                )

        except Exception:

            pass

    (
        total,
        won,
        lost,
        pending,
        effectiveness,
        profit
    ) = calculate_stats(
        selected
    )

    return f"""
📆 RENDIMIENTO ÚLTIMOS 7 DÍAS

📥 Señales: {total}

✅ Ganadas: {won}
❌ Perdidas: {lost}
⏳ Pendientes: {pending}

🎯 Efectividad:
{effectiveness:.1f}%

💰 Ganancia:
${profit:,.0f} COP
"""


# ============================================================
# MES
# ============================================================

def month_panel():

    signals = load_signals()

    now = datetime.now(
        timezone.utc
    )

    selected = []

    for signal in signals:

        try:

            registered = datetime.strptime(
                signal["registered_at"],
                "%Y-%m-%d %H:%M:%S"
            ).replace(
                tzinfo=timezone.utc
            )

            if (
                registered.year
                == now.year
                and
                registered.month
                == now.month
            ):

                selected.append(
                    signal
                )

        except Exception:

            pass

    (
        total,
        won,
        lost,
        pending,
        effectiveness,
        profit
    ) = calculate_stats(
        selected
    )

    return f"""
🗓 RENDIMIENTO DEL MES

📥 Señales: {total}

✅ Ganadas: {won}
❌ Perdidas: {lost}
⏳ Pendientes: {pending}

🎯 Efectividad:
{effectiveness:.1f}%

💰 Ganancia:
${profit:,.0f} COP
"""


# ============================================================
# CALENDARIO
# ============================================================

def calendar_panel():

    signals = load_signals()

    if not signals:

        return (
            "📅 Todavía no hay señales."
        )

    grouped = {}

    for signal in signals:

        date = signal.get(
            "registered_at",
            ""
        )[:10]

        if date:

            if date not in grouped:

                grouped[date] = []

            grouped[date].append(
                signal
            )

    output = """
╔════════════════════════════╗
║       📅 CALENDARIO         ║
╚════════════════════════════╝
"""

    for date in sorted(
        grouped.keys(),
        reverse=True
    ):

        items = grouped[
            date
        ]

        won = sum(
            1
            for s in items
            if s.get(
                "result"
            ) == "GANADA"
        )

        lost = sum(
            1
            for s in items
            if s.get(
                "result"
            ) == "PERDIDA"
        )

        pending = sum(
            1
            for s in items
            if s.get(
                "result"
            ) == "PENDIENTE"
        )

        output += f"""

📆 {date}

📥 {len(items)}
✅ {won}
❌ {lost}
⏳ {pending}

"""

    return output


# ============================================================
# ACTUALIZAR RESULTADO MANUAL
# ============================================================

def update_result(
    signal_id,
    result
):

    signals = load_signals()

    for signal in signals:

        if signal.get(
            "id"
        ) == signal_id:

            signal[
                "result"
            ] = result

            odds = signal.get(
                "odds"
            )

            if result == "GANADA":

                if odds:

                    signal[
                        "profit"
                    ] = (
                        BET_AMOUNT
                        *
                        (
                            odds - 1
                        )
                    )

                else:

                    signal[
                        "profit"
                    ] = BET_AMOUNT

            elif result == "PERDIDA":

                signal[
                    "profit"
                ] = -BET_AMOUNT

            save_signals(
                signals
            )

            return True

    return False


# ============================================================
# PROCESAR MENSAJES
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
        "Procesando mensaje:",
        text[:100]
    )

    # ========================================================
    # COMANDOS — TIENEN PRIORIDAD ABSOLUTA
    # ========================================================

    command = text.split()[0].lower()

    if command == "/start":

        send_message(
            chat_id,
            """
🤖 APUESTASMURCIA BOT

🟢 Bot conectado.

📊 /panel
🎯 /estrategias
⏳ /pendientes
📅 /hoy
📆 /semana
🗓 /mes
📅 /calendario

También puedes enviar
alertas de BetMines.
"""
        )

        return

    if command == "/panel":

        send_message(
            chat_id,
            panel()
        )

        return

    if command == "/estrategias":

        send_message(
            chat_id,
            strategies_panel()
        )

        return

    if command == "/pendientes":

        send_message(
            chat_id,
            pending_panel()
        )

        return

    if command == "/hoy":

        send_message(
            chat_id,
            today_panel()
        )

        return

    if command == "/semana":

        send_message(
            chat_id,
            week_panel()
        )

        return

    if command == "/mes":

        send_message(
            chat_id,
            month_panel()
        )

        return

    if command == "/calendario":

        send_message(
            chat_id,
            calendar_panel()
        )

        return

    # ========================================================
    # RESULTADOS MANUALES
    # ========================================================

    match = re.match(
        r"^/ganada\s+(\d+)$",
        text,
        re.IGNORECASE
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
                f"✅ Señal #{signal_id} marcada como GANADA."
            )

        else:

            send_message(
                chat_id,
                f"❌ No existe la señal #{signal_id}."
            )

        return

    match = re.match(
        r"^/perdida\s+(\d+)$",
        text,
        re.IGNORECASE
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
                f"❌ Señal #{signal_id} marcada como PERDIDA."
            )

        else:

            send_message(
                chat_id,
                f"❌ No existe la señal #{signal_id}."
            )

        return

    # ========================================================
    # OTROS COMANDOS
    # ========================================================

    if text.startswith("/"):

        print(
            "Comando no reconocido:",
            text
        )

        return

    # ========================================================
    # ALERTA BETMINES
    # ========================================================

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
╔════════════════════════════╗
║    📥 SEÑAL REGISTRADA     ║
╚════════════════════════════╝

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
{odds_text}

⏳ ESTADO:
PENDIENTE

━━━━━━━━━━━━━━━━━━━━

📊 /panel
🎯 /estrategias
⏳ /pendientes
📅 /calendario
"""
    )


# ============================================================
# EJECUCIÓN
# ============================================================

def collect_messages():

    offset = load_offset()

    print(
        "Offset actual:",
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

        if update_id is None:
            continue

        try:

            if "message" in update:

                process_message(
                    update["message"]
                )

        except Exception as e:

            print(
                "Error procesando mensaje:",
                e
            )

        # Guardamos el offset DESPUÉS
        # de procesar el mensaje

        save_offset(
            update_id + 1
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "======================================"
    )

    print(
        "       APUESTASMURCIA BOT"
    )

    print(
        "======================================"
    )

    print(
        "Revisando Telegram..."
    )

    collect_messages()

    print(
        "Ejecución terminada correctamente."
    )