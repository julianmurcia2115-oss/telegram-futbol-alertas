import os
import re
import json
import time
import base64
import requests
from datetime import datetime, timezone, timedelta

# ============================================================
# CONFIGURACION
# ============================================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

FOOTBALL_DATA_API_KEY = os.environ.get(
    "FOOTBALL_DATA_API_KEY"
)

GITHUB_TOKEN = os.environ.get(
    "GITHUB_TOKEN"
)

GITHUB_REPOSITORY = os.environ.get(
    "GITHUB_REPOSITORY"
)

DATA_FILE = "signals.json"

BET_AMOUNT = 5000

TELEGRAM_URL = (
    f"https://api.telegram.org/bot{BOT_TOKEN}"
)

FOOTBALL_URL = (
    "https://footballdata.io/api/v1"
)

GITHUB_API = (
    "https://api.github.com"
)


# ============================================================
# GITHUB - PERSISTENCIA
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


def load_signals():

    # Primero intenta GitHub

    if GITHUB_TOKEN and GITHUB_REPOSITORY:

        try:

            url = (
                f"{GITHUB_API}/repos/"
                f"{GITHUB_REPOSITORY}/contents/"
                f"{DATA_FILE}"
            )

            r = requests.get(
                url,
                headers=github_headers(),
                timeout=30
            )

            if r.ok:

                data = r.json()

                content = base64.b64decode(
                    data["content"]
                ).decode(
                    "utf-8"
                )

                return json.loads(
                    content
                )

        except Exception as e:

            print(
                "Error leyendo GitHub:",
                e
            )

    # Respaldo local

    if os.path.exists(DATA_FILE):

        try:

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                return json.load(f)

        except Exception:

            pass

    return []


def save_signals(signals):

    # Guardar local

    try:

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

    except Exception as e:

        print(
            "Error guardando local:",
            e
        )

    # Guardar en GitHub

    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:

        print(
            "GITHUB_TOKEN no disponible."
        )

        return False

    try:

        url = (
            f"{GITHUB_API}/repos/"
            f"{GITHUB_REPOSITORY}/contents/"
            f"{DATA_FILE}"
        )

        r = requests.get(
            url,
            headers=github_headers(),
            timeout=30
        )

        sha = None

        if r.ok:

            sha = r.json().get(
                "sha"
            )

        content = base64.b64encode(
            json.dumps(
                signals,
                ensure_ascii=False,
                indent=2
            ).encode(
                "utf-8"
            )
        ).decode(
            "utf-8"
        )

        payload = {

            "message":
                "Actualizar señales del bot",

            "content":
                content
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
                "signals.json guardado en GitHub."
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
            "Error Telegram:",
            e
        )

        return False


# ============================================================
# API FOOTBALLDATA
# ============================================================

def football_get(
    endpoint,
    params=None
):

    if not FOOTBALL_DATA_API_KEY:

        print(
            "FOOTBALL_DATA_API_KEY no configurada."
        )

        return None

    try:

        headers = {

            "Authorization":
                f"Bearer {FOOTBALL_DATA_API_KEY}",

            "Accept":
                "application/json"
        }

        r = requests.get(
            f"{FOOTBALL_URL}/{endpoint}",
            headers=headers,
            params=params or {},
            timeout=30
        )

        data = r.json()

        if not r.ok:

            print(
                "Error Footballdata:",
                r.status_code,
                data
            )

            return None

        if data.get(
            "success"
        ) is False:

            print(
                "Error Footballdata:",
                data
            )

            return None

        return data

    except Exception as e:

        print(
            "Error API:",
            e
        )

        return None


def extract_list(data):

    if not data:

        return []

    value = data.get(
        "data"
    )

    if isinstance(
        value,
        list
    ):

        return value

    if isinstance(
        value,
        dict
    ):

        for key in [
            "matches",
            "fixtures",
            "results"
        ]:

            if isinstance(
                value.get(key),
                list
            ):

                return value[key]

    return []


# ============================================================
# TEXTO
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


def clean_value(
    value
):

    if not value:

        return "No identificado"

    return value.strip()


# ============================================================
# ESTRATEGIAS
# ============================================================

def extract_strategy(text):

    patterns = [

        r"Resultado\s*deseado\s*:\s*(.+)",

        r"Estrategia\s*:\s*(.+)"
    ]

    for pattern in patterns:

        value = extract(
            text,
            pattern,
            ""
        )

        if value:

            return value.strip()

    low = text.lower()

    strategies = [

        (
            "local gana",
            "Victoria Local"
        ),

        (
            "victoria local",
            "Victoria Local"
        ),

        (
            "home win",
            "Victoria Local"
        ),

        (
            "visitante gana",
            "Victoria Visitante"
        ),

        (
            "victoria visitante",
            "Victoria Visitante"
        ),

        (
            "away win",
            "Victoria Visitante"
        ),

        (
            "ambos marcan",
            "Ambos Marcan"
        ),

        (
            "btts",
            "Ambos Marcan"
        ),

        (
            "más de 2.5",
            "Más de 2.5"
        ),

        (
            "over 2.5",
            "Más de 2.5"
        ),

        (
            "menos de 2.5",
            "Menos de 2.5"
        ),

        (
            "under 2.5",
            "Menos de 2.5"
        ),

        (
            "empate 1t",
            "Empate 1T"
        ),

        (
            "empate 1er tiempo",
            "Empate 1T"
        ),

        (
            "empate",
            "Empate"
        ),

        (
            "draw",
            "Empate"
        )
    ]

    for keyword, name in strategies:

        if keyword in low:

            return name

    return "OTRA"


# ============================================================
# DATOS BETMINES
# ============================================================

def extract_odds(text):

    patterns = [

        r"bet365:\s*([\d.,]+)",

        r"Cuota:\s*([\d.,]+)",

        r"cuota:\s*([\d.,]+)"
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
                    value.replace(
                        ",",
                        "."
                    )
                )

            except Exception:

                pass

    return None


def extract_success(text):

    value = extract(
        text,
        r"Success Percentage:\s*([\d.,]+)\s*%",
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


def extract_roi(text):

    value = extract(
        text,
        r"ROI:\s*([+-]?[\d.,]+)\s*%",
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


def extract_picks(text):

    value = extract(
        text,
        r"picks:\s*(\d+)",
        ""
    )

    if not value:

        return None

    try:

        return int(value)

    except Exception:

        return None


def extract_ranking(text):

    return extract(
        text,
        r"Posición\s+en\s+el\s+ranking:\s*(.+)"
    )


# ============================================================
# REGISTRAR SEÑAL
# ============================================================

def register_signal(text):

    signals = load_signals()

    strategy = extract_strategy(
        text
    )

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
            clean_value(
                extract(
                    text,
                    r"🏆\s*(.+)"
                )
            ),

        "match":
            clean_value(
                extract(
                    text,
                    r"🆚\s*(.+)"
                )
            ),

        "date":
            clean_value(
                extract(
                    text,
                    r"🗓\s*(.+)"
                )
            ),

        "strategy":
            strategy,

        "desired_result":
            clean_value(
                extract(
                    text,
                    r"Resultado\s*deseado\s*:\s*(.+)"
                )
            ),

        "odds":
            extract_odds(text),

        "success":
            extract_success(text),

        "roi":
            extract_roi(text),

        "picks":
            extract_picks(text),

        "ranking":
            extract_ranking(text),

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
# FECHAS
# ============================================================

MONTHS = {

    "ene": 1,
    "enero": 1,

    "feb": 2,
    "febrero": 2,

    "mar": 3,
    "marzo": 3,

    "abr": 4,
    "abril": 4,

    "may": 5,
    "mayo": 5,

    "jun": 6,
    "junio": 6,

    "jul": 7,
    "julio": 7,

    "ago": 8,
    "agosto": 8,

    "sep": 9,
    "sept": 9,
    "septiembre": 9,

    "oct": 10,
    "octubre": 10,

    "nov": 11,
    "noviembre": 11,

    "dic": 12,
    "diciembre": 12
}


def parse_date(text):

    if not text:

        return None

    # 2026-08-23

    m = re.search(
        r"(20\d{2})-(\d{1,2})-(\d{1,2})",
        text
    )

    if m:

        return (
            f"{m.group(1)}-"
            f"{int(m.group(2)):02d}-"
            f"{int(m.group(3)):02d}"
        )

    # 23 ago 2026

    m = re.search(
        r"(\d{1,2})\s+"
        r"([A-Za-záéíóúñ]+)\s+"
        r"(20\d{2})",
        text,
        re.IGNORECASE
    )

    if m:

        day = int(
            m.group(1)
        )

        month = MONTHS.get(
            m.group(2).lower()
        )

        year = int(
            m.group(3)
        )

        if month:

            return (
                f"{year}-"
                f"{month:02d}-"
                f"{day:02d}"
            )

    return None


# ============================================================
# EQUIPOS
# ============================================================

def normalize_name(name):

    if not name:

        return ""

    name = name.lower()

    replacements = {

        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n"
    }

    for a, b in replacements.items():

        name = name.replace(
            a,
            b
        )

    name = re.sub(
        r"[^a-z0-9\s]",
        " ",
        name
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip()


def names_match(
    a,
    b
):

    a = normalize_name(a)
    b = normalize_name(b)

    if not a or not b:

        return False

    if a == b:

        return True

    if a in b or b in a:

        return True

    words_a = set(
        a.split()
    )

    words_b = set(
        b.split()
    )

    common = words_a.intersection(
        words_b
    )

    return len(common) >= 1


def split_match(match):

    parts = re.split(
        r"\s+(?:vs|v)\s+|\s+-\s+",
        match,
        maxsplit=1,
        flags=re.IGNORECASE
    )

    if len(parts) != 2:

        return None, None

    return (
        parts[0].strip(),
        parts[1].strip()
    )


# ============================================================
# RESULTADOS
# ============================================================

def get_matches_by_date(
    date
):

    data = football_get(
        f"matches/date/{date}"
    )

    return extract_list(
        data
    )


def get_match_score(
    match
):

    score = match.get(
        "score",
        {}
    )

    if not isinstance(
        score,
        dict
    ):

        score = {}

    home = score.get(
        "home"
    )

    away = score.get(
        "away"
    )

    if home is None:

        home = score.get(
            "home_score"
        )

    if away is None:

        away = score.get(
            "away_score"
        )

    try:

        return (
            int(home),
            int(away)
        )

    except Exception:

        return None, None


def get_match_teams(
    match
):

    home = match.get(
        "home_team",
        {}
    )

    away = match.get(
        "away_team",
        {}
    )

    if not home:

        home = match.get(
            "home",
            {}
        )

    if not away:

        away = match.get(
            "away",
            {}
        )

    if isinstance(
        home,
        dict
    ):

        home_name = (
            home.get(
                "team_name"
            )
            or
            home.get(
                "name"
            )
            or ""
        )

    else:

        home_name = str(home)

    if isinstance(
        away,
        dict
    ):

        away_name = (
            away.get(
                "team_name"
            )
            or
            away.get(
                "name"
            )
            or ""
        )

    else:

        away_name = str(away)

    return (
        home_name,
        away_name
    )


def match_finished(
    match
):

    status = match.get(
        "status"
    )

    if isinstance(
        status,
        dict
    ):

        status = (
            status.get(
                "short"
            )
            or
            status.get(
                "name"
            )
            or
            ""
        )

    status = str(
        status
    ).lower()

    finished = [

        "complete",
        "completed",
        "finished",
        "ft",
        "after",
        "final"
    ]

    return any(
        x in status
        for x in finished
    )


def find_match(
    signal
):

    date = parse_date(
        signal.get(
            "date",
            ""
        )
    )

    if not date:

        return None

    home_name, away_name = (
        split_match(
            signal.get(
                "match",
                ""
            )
        )
    )

    if not home_name or not away_name:

        return None

    matches = get_matches_by_date(
        date
    )

    for match in matches:

        api_home, api_away = (
            get_match_teams(
                match
            )
        )

        if (
            names_match(
                home_name,
                api_home
            )
            and
            names_match(
                away_name,
                api_away
            )
        ):

            return match

    return None


# ============================================================
# EVALUAR APUESTA
# ============================================================

def evaluate_result(
    strategy,
    home,
    away
):

    s = normalize_name(
        strategy
    )

    total = (
        home + away
    )

    # Victoria local

    if (
        "victoria local" in s
        or
        "local gana" in s
        or
        "home win" in s
    ):

        return (
            "GANADA"
            if home > away
            else "PERDIDA"
        )

    # Victoria visitante

    if (
        "victoria visitante" in s
        or
        "visitante gana" in s
        or
        "away win" in s
    ):

        return (
            "GANADA"
            if away > home
            else "PERDIDA"
        )

    # Empate

    if (
        s == "empate"
        or
        s == "draw"
    ):

        return (
            "GANADA"
            if home == away
            else "PERDIDA"
        )

    # BTTS

    if (
        "ambos marcan" in s
        or
        "btts" in s
    ):

        return (
            "GANADA"
            if home > 0 and away > 0
            else "PERDIDA"
        )

    # Over

    if (
        "mas de 2.5" in s
        or
        "over 2.5" in s
    ):

        return (
            "GANADA"
            if total >= 3
            else "PERDIDA"
        )

    # Under

    if (
        "menos de 2.5" in s
        or
        "under 2.5" in s
    ):

        return (
            "GANADA"
            if total <= 2
            else "PERDIDA"
        )

    # Resultado deseado puede venir
    # en lugar de estrategia

    return None


# ============================================================
# REVISAR RESULTADOS
# ============================================================

def check_results():

    signals = load_signals()

    changed = False

    for signal in signals:

        if signal.get(
            "result"
        ) != "PENDIENTE":

            continue

        match = find_match(
            signal
        )

        if not match:

            continue

        if not match_finished(
            match
        ):

            continue

        home, away = (
            get_match_score(
                match
            )
        )

        if home is None:

            continue

        result = evaluate_result(
            signal.get(
                "strategy",
                "OTRA"
            ),
            home,
            away
        )

        if result is None:

            print(
                f"#{signal['id']} "
                f"estrategia no evaluable: "
                f"{signal.get('strategy')}"
            )

            continue

        signal["result"] = result

        signal["final_score"] = (
            f"{home}-{away}"
        )

        odds = signal.get(
            "odds"
        )

        if result == "GANADA":

            if odds:

                signal["profit"] = (
                    BET_AMOUNT
                    * (odds - 1)
                )

            else:

                signal["profit"] = (
                    BET_AMOUNT
                )

        else:

            signal["profit"] = (
                -BET_AMOUNT
            )

        signal["settled_at"] = (
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        print(
            f"RESULTADO #{signal['id']}: "
            f"{result} "
            f"{home}-{away}"
        )

        changed = True

    if changed:

        save_signals(
            signals
        )


# ============================================================
# CALCULOS
# ============================================================

def period_signals(
    signals,
    days
):

    today = datetime.now(
        timezone.utc
    ).date()

    result = []

    for signal in signals:

        registered = signal.get(
            "registered_at"
        )

        try:

            date = datetime.strptime(
                registered,
                "%Y-%m-%d %H:%M:%S"
            ).date()

        except Exception:

            continue

        if (
            today - date
        ).days < days:

            result.append(
                signal
            )

    return result


def calculate_stats(
    signals
):

    total = len(
        signals
    )

    won = sum(
        1
        for s in signals
        if s.get(
            "result"
        ) == "GANADA"
    )

    lost = sum(
        1
        for s in signals
        if s.get(
            "result"
        ) == "PERDIDA"
    )

    pending = sum(
        1
        for s in signals
        if s.get(
            "result"
        ) == "PENDIENTE"
    )

    finished = (
        won + lost
    )

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

    invested = (
        finished * BET_AMOUNT
    )

    return {
        "total": total,
        "won": won,
        "lost": lost,
        "pending": pending,
        "effectiveness": effectiveness,
        "profit": profit,
        "invested": invested
    }


# ============================================================
# PANEL PRINCIPAL
# ============================================================

def panel():

    signals = load_signals()

    stats = calculate_stats(
        signals
    )

    today = calculate_stats(
        period_signals(
            signals,
            1
        )
    )

    week = calculate_stats(
        period_signals(
            signals,
            7
        )
    )

    month = calculate_stats(
        period_signals(
            signals,
            30
        )
    )

    return f"""
╔══════════════════════════╗
║     APUESTASMURCIA       ║
║       DASHBOARD          ║
╚══════════════════════════╝

💵 APUESTA: $5.000 COP

━━━━━━━━━━━━━━━━━━━━
📊 GENERAL
━━━━━━━━━━━━━━━━━━━━

📥 Señales: {stats['total']}
✅ Ganadas: {stats['won']}
❌ Perdidas: {stats['lost']}
⏳ Pendientes: {stats['pending']}

🎯 Efectividad:
{stats['effectiveness']:.1f}%

💰 Ganancia:
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
📅 HOY
━━━━━━━━━━━━━━━━━━━━

📥 {today['total']} señales
✅ {today['won']} | ❌ {today['lost']}
💰 ${today['profit']:,.0f}

━━━━━━━━━━━━━━━━━━━━
📆 ÚLTIMOS 7 DÍAS
━━━━━━━━━━━━━━━━━━━━

📥 {week['total']} señales
✅ {week['won']} | ❌ {week['lost']}
🎯 {week['effectiveness']:.1f}%
💰 ${week['profit']:,.0f}

━━━━━━━━━━━━━━━━━━━━
🗓️ ÚLTIMOS 30 DÍAS
━━━━━━━━━━━━━━━━━━━━

📥 {month['total']} señales
✅ {month['won']} | ❌ {month['lost']}
🎯 {month['effectiveness']:.1f}%
💰 ${month['profit']:,.0f}

━━━━━━━━━━━━━━━━━━━━

📌 /hoy
📌 /semana
📌 /mes
📌 /calendario
📌 /estrategias
📌 /pendientes
"""


# ============================================================
# PANEL DIARIO
# ============================================================

def today_panel():

    signals = load_signals()

    today = datetime.now(
        timezone.utc
    ).date()

    selected = []

    for signal in signals:

        date = parse_date(
            signal.get(
                "date",
                ""
            )
        )

        if date == str(today):

            selected.append(
                signal
            )

    stats = calculate_stats(
        selected
    )

    output = f"""
╔══════════════════════════╗
║       📅 HOY             ║
╚══════════════════════════╝

📅 {today}

📥 Señales: {stats['total']}
✅ Ganadas: {stats['won']}
❌ Perdidas: {stats['lost']}
⏳ Pendientes: {stats['pending']}

🎯 Efectividad:
{stats['effectiveness']:.1f}%

💰 Ganancia:
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
"""

    for signal in selected:

        emoji = "⏳"

        if signal["result"] == "GANADA":

            emoji = "✅"

        elif signal["result"] == "PERDIDA":

            emoji = "❌"

        output += (
            f"\n{emoji} #{signal['id']} "
            f"{signal['match']}\n"
            f"🎯 {signal['strategy']}\n"
            f"💰 {signal.get('odds') or 'N/D'}\n"
        )

    return output


# ============================================================
# SEMANA
# ============================================================

def week_panel():

    signals = load_signals()

    selected = period_signals(
        signals,
        7
    )

    stats = calculate_stats(
        selected
    )

    return f"""
╔══════════════════════════╗
║       📆 SEMANA          ║
╚══════════════════════════╝

📥 Señales: {stats['total']}

✅ Ganadas: {stats['won']}
❌ Perdidas: {stats['lost']}
⏳ Pendientes: {stats['pending']}

🎯 Efectividad:
{stats['effectiveness']:.1f}%

💵 Apostado:
${stats['invested']:,.0f}

💰 GANANCIA:
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━

📌 Apuesta fija:
$5.000 por señal
"""


# ============================================================
# MES
# ============================================================

def month_panel():

    signals = load_signals()

    selected = period_signals(
        signals,
        30
    )

    stats = calculate_stats(
        selected
    )

    return f"""
╔══════════════════════════╗
║        🗓️ MES            ║
╚══════════════════════════╝

📥 Señales: {stats['total']}

✅ Ganadas: {stats['won']}
❌ Perdidas: {stats['lost']}
⏳ Pendientes: {stats['pending']}

🎯 Efectividad:
{stats['effectiveness']:.1f}%

💵 Total apostado:
${stats['invested']:,.0f}

💰 GANANCIA:
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
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
            "OTRA"
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

        stats = calculate_stats(
            items
        )

        output += f"""

🏷️ {strategy}

📥 {stats['total']} señales
✅ {stats['won']} | ❌ {stats['lost']}
⏳ {stats['pending']} pendientes

🎯 Efectividad:
{stats['effectiveness']:.1f}%

💰 Ganancia:
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
"""

    return output


# ============================================================
# PENDIENTES
# ============================================================

def pending_panel():

    signals = load_signals()

    pending = [

        s
        for s in signals
        if s.get(
            "result"
        ) == "PENDIENTE"
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

⚽ {signal['match']}

🏆 {signal['league']}

🎯 {signal['strategy']}

💰 Cuota:
{signal.get('odds') or 'N/D'}

━━━━━━━━━━━━━━━━━━━━
"""

    return output


# ============================================================
# CALENDARIO VISUAL
# ============================================================

def calendar_panel():

    signals = load_signals()

    now = datetime.now(
        timezone.utc
    )

    year = now.year
    month = now.month

    days = {}

    for signal in signals:

        date = parse_date(
            signal.get(
                "date",
                ""
            )
        )

        if not date:

            continue

        try:

            d = datetime.strptime(
                date,
                "%Y-%m-%d"
            ).date()

        except Exception:

            continue

        if (
            d.year == year
            and d.month == month
        ):

            if d.day not in days:

                days[d.day] = {
                    "won": 0,
                    "lost": 0,
                    "pending": 0,
                    "profit": 0
                }

            result = signal.get(
                "result"
            )

            if result == "GANADA":

                days[d.day]["won"] += 1

            elif result == "PERDIDA":

                days[d.day]["lost"] += 1

            else:

                days[d.day]["pending"] += 1

            days[d.day]["profit"] += (
                signal.get(
                    "profit",
                    0
                )
            )

    output = f"""
╔══════════════════════════╗
║       📅 CALENDARIO      ║
╚══════════════════════════╝

        {year}-{month:02d}

Lu  Ma  Mi  Ju  Vi  Sá  Do
"""

    first = datetime(
        year,
        month,
        1
    )

    offset = first.weekday()

    output += (
        "    " * offset
    )

    # Número de días

    if month == 12:

        next_month = datetime(
            year + 1,
            1,
            1
        )

    else:

        next_month = datetime(
            year,
            month + 1,
            1
        )

    days_in_month = (
        next_month
        - first
    ).days

    for day in range(
        1,
        days_in_month + 1
    ):

        if day in days:

            data = days[day]

            if data["won"] > 0 and data["lost"] == 0:

                symbol = "🟢"

            elif data["lost"] > 0 and data["won"] == 0:

                symbol = "🔴"

            elif data["won"] > 0 and data["lost"] > 0:

                symbol = "🟡"

            else:

                symbol = "⚪"

            cell = (
                f"{symbol}{day:02d}"
            )

        else:

            cell = f"  {day:02d}"

        output += cell + " "

        if (
            first.weekday()
            + day
        ) % 7 == 0:

            output += "\n"

    output += """

━━━━━━━━━━━━━━━━━━━━

🟢 Ganada
🔴 Perdida
🟡 Mixto
⚪ Sin señales

Usa /hoy para ver
el detalle del día.
"""

    return output


# ============================================================
# COMANDOS
# ============================================================

def process_message(
    message
):

    chat_id = message[
        "chat"
    ]["id"]

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
╔══════════════════════════╗
║   APUESTASMURCIA BOT     ║
╚══════════════════════════╝

🟢 BOT ACTIVO

Envíame cualquier alerta
de BetMines.

📊 /panel
📅 /hoy
📆 /semana
🗓️ /mes
📅 /calendario
🎯 /estrategias
⏳ /pendientes

💵 Apuesta:
$5.000 COP

Los resultados reconocibles
se actualizarán automáticamente.
"""
        )

        return

    if text == "/panel":

        check_results()

        send_message(
            chat_id,
            panel()
        )

        return

    if text == "/hoy":

        check_results()

        send_message(
            chat_id,
            today_panel()
        )

        return

    if text == "/semana":

        check_results()

        send_message(
            chat_id,
            week_panel()
        )

        return

    if text == "/mes":

        check_results()

        send_message(
            chat_id,
            month_panel()
        )

        return

    if text == "/calendario":

        check_results()

        send_message(
            chat_id,
            calendar_panel()
        )

        return

    if text == "/estrategias":

        check_results()

        send_message(
            chat_id,
            strategies_panel()
        )

        return

    if text == "/pendientes":

        check_results()

        send_message(
            chat_id,
            pending_panel()
        )

        return

    # ========================================================
    # COMANDO MANUAL GANADA
    # ========================================================

    m = re.match(
        r"^/ganada\s+(\d+)$",
        text,
        re.IGNORECASE
    )

    if m:

        signal_id = int(
            m.group(1)
        )

        signals = load_signals()

        found = False

        for signal in signals:

            if signal["id"] == signal_id:

                signal["result"] = (
                    "GANADA"
                )

                odds = signal.get(
                    "odds"
                )

                signal["profit"] = (
                    BET_AMOUNT *
                    (odds - 1)
                    if odds
                    else BET_AMOUNT
                )

                found = True

                break

        if found:

            save_signals(
                signals
            )

            send_message(
                chat_id,
                f"✅ Señal #{signal_id} marcada como GANADA."
            )

        else:

            send_message(
                chat_id,
                "❌ Señal no encontrada."
            )

        return

    # ========================================================
    # COMANDO MANUAL PERDIDA
    # ========================================================

    m = re.match(
        r"^/perdida\s+(\d+)$",
        text,
        re.IGNORECASE
    )

    if m:

        signal_id = int(
            m.group(1)
        )

        signals = load_signals()

        found = False

        for signal in signals:

            if signal["id"] == signal_id:

                signal["result"] = (
                    "PERDIDA"
                )

                signal["profit"] = (
                    -BET_AMOUNT
                )

                found = True

                break

        if found:

            save_signals(
                signals
            )

            send_message(
                chat_id,
                f"❌ Señal #{signal_id} marcada como PERDIDA."
            )

        else:

            send_message(
                chat_id,
                "❌ Señal no encontrada."
            )

        return

    # ========================================================
    # NUEVA ALERTA
    # ========================================================

    signal = register_signal(
        text
    )

    message_text = f"""
╔══════════════════════════╗
║   📥 SEÑAL REGISTRADA    ║
╚══════════════════════════╝

🆔 #{signal['id']}

🏆 {signal['league']}

⚽ {signal['match']}

📅 {signal['date']}

🎯 Estrategia:
{signal['strategy']}

💰 Cuota:
{signal.get('odds') or 'N/D'}

📊 Success:
{signal.get('success') if signal.get('success') is not None else 'N/D'}%

📈 ROI:
{signal.get('roi') if signal.get('roi') is not None else 'N/D'}%

🎯 Picks:
{signal.get('picks') or 'N/D'}

🏅 Ranking:
{signal.get('ranking') or 'No identificado'}

⏳ ESTADO:
PENDIENTE

━━━━━━━━━━━━━━━━━━━━

📊 /panel
🎯 /estrategias
📅 /hoy
📆 /semana
🗓️ /mes
📅 /calendario
⏳ /pendientes
"""

    send_message(
        chat_id,
        message_text
    )


# ============================================================
# BOT
# ============================================================

def run_bot():

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
        "Bot iniciado."
    )

    print(
        "Esperando alertas..."
    )

    if FOOTBALL_DATA_API_KEY:

        print(
            "FOOTBALLDATA: CONFIGURADA"
        )

    else:

        print(
            "FOOTBALLDATA: NO CONFIGURADA"
        )

    offset = None

    start_time = time.time()

    # Cada ejecución trabaja unos 9 minutos.
    # Así GitHub Actions puede iniciar
    # una nueva ejecución cada 10 minutos.

    while (
        time.time() - start_time
        < 540
    ):

        try:

            # Revisar resultados

            check_results()

            params = {
                "timeout": 30
            }

            if offset is not None:

                params[
                    "offset"
                ] = offset

            r = requests.get(
                f"{TELEGRAM_URL}/getUpdates",
                params=params,
                timeout=40
            )

            data = r.json()

            if not data.get(
                "ok"
            ):

                print(
                    "Telegram:",
                    data
                )

                time.sleep(5)

                continue

            for update in data.get(
                "result",
                []
            ):

                offset = (
                    update[
                        "update_id"
                    ] + 1
                )

                if "message" in update:

                    process_message(
                        update[
                            "message"
                        ]
                    )

        except Exception as e:

            print(
                "Error:",
                e
            )

            time.sleep(5)

    print(
        "Ejecución finalizada."
    )


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":

    run_bot()