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
FOOTBALLDATA_API_KEY = os.environ.get("FOOTBALLDATA_API_KEY", "").strip()

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SIGNALS_FILE = "signals.json"
OFFSET_FILE = "telegram_offset.json"

BET_AMOUNT = 5000

COLOMBIA_TZ = ZoneInfo("America/Bogota")

# =========================================================
# HORA
# =========================================================

def colombia_now():
    return datetime.now(COLOMBIA_TZ)


def colombia_date():
    return colombia_now().strftime("%Y-%m-%d")


def colombia_datetime():
    return colombia_now().strftime("%Y-%m-%d %H:%M:%S")


# =========================================================
# TELEGRAM
# =========================================================

def telegram_request(method, data=None):

    try:
        r = requests.post(
            f"{TELEGRAM_URL}/{method}",
            data=data or {},
            timeout=30
        )

        result = r.json()

        if not result.get("ok"):
            print("❌ Telegram:", result)

        return result

    except Exception as e:
        print("❌ Telegram:", e)
        return {"ok": False}


def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps({
            "inline_keyboard": keyboard
        })

    return telegram_request("sendMessage", data)


def edit_message(chat_id, message_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = json.dumps({
            "inline_keyboard": keyboard
        })

    return telegram_request("editMessageText", data)


def answer_callback(callback_id):

    return telegram_request(
        "answerCallbackQuery",
        {"callback_query_id": callback_id}
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
        ) as f:
            data = json.load(f)

        return data if isinstance(data, list) else []

    except Exception as e:
        print("❌ Error signals.json:", e)
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
        print("❌ Error guardando señales:", e)
        return False


# =========================================================
# OFFSET TELEGRAM
# =========================================================

def load_offset():

    if not os.path.exists(OFFSET_FILE):
        return None

    try:
        with open(
            OFFSET_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f).get("offset")

    except Exception:
        return None


def save_offset(offset):

    try:
        with open(
            OFFSET_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                {"offset": offset},
                f
            )

    except Exception as e:
        print("❌ Error offset:", e)


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
                "text": "⏳ Pendientes",
                "callback_data": "pendientes"
            },
            {
                "text": "💰 Ganancias",
                "callback_data": "ganancias"
            }
        ],
        [
            {
                "text": "📈 Estadísticas",
                "callback_data": "estadisticas"
            },
            {
                "text": "⚙️ Configuración",
                "callback_data": "configuracion"
            }
        ]
    ]


def back_keyboard():

    return [[
        {
            "text": "⬅️ Volver",
            "callback_data": "inicio"
        }
    ]]


# =========================================================
# EXTRACCIÓN
# =========================================================

def extract(text, patterns, default=""):

    if isinstance(patterns, str):
        patterns = [patterns]

    for pattern in patterns:

        m = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if m:
            return m.group(1).strip()

    return default


def extract_strategy(text):

    lower = text.lower()

    if "menos de 3.5" in lower or "under 3.5" in lower:
        return "Menos de 3.5 goles"

    if "menos de 2.5" in lower or "under 2.5" in lower:
        return "Menos de 2.5 goles"

    if "más de 3.5" in lower or "over 3.5" in lower:
        return "Más de 3.5 goles"

    if "más de 2.5" in lower or "over 2.5" in lower:
        return "Más de 2.5 goles"

    if "ambos marcan" in lower or "btts" in lower:
        return "Ambos Marcan"

    if (
        "empate" in lower
        and (
            "primer tiempo" in lower
            or "1er tiempo" in lower
        )
    ):
        return "Empate Primer Tiempo"

    if "victoria local" in lower:
        return "Victoria Local"

    if "victoria visitante" in lower:
        return "Victoria Visitante"

    result = extract(
        text,
        [
            r"Resultado\s*deseado\s*:\s*(.+)",
            r"Estrategia\s*:\s*(.+)",
            r"Mercado\s*:\s*(.+)"
        ]
    )

    return result if result else "SIN ESTRATEGIA"


def extract_odds(text):

    value = extract(
        text,
        [
            r"bet365\s*:\s*([\d.,]+)",
            r"cuota\s*:\s*([\d.,]+)"
        ]
    )

    if not value:
        return None

    try:
        return float(
            value.replace(",", ".")
        )
    except:
        return None


# =========================================================
# FECHA DE LA SEÑAL
# =========================================================

def extract_signal_date(text):

    value = extract(
        text,
        [
            r"🗓\s*(.+)",
            r"Fecha\s*:\s*(.+)"
        ]
    )

    if not value:
        return None

    months = {
        "ene": 1,
        "feb": 2,
        "mar": 3,
        "abr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "ago": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dic": 12
    }

    m = re.search(
        r"(\d{1,2})\s+"
        r"(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)"
        r"\s+(\d{4})",
        value.lower()
    )

    if m:

        day = int(m.group(1))
        month = months[m.group(2)]
        year = int(m.group(3))

        return f"{year:04d}-{month:02d}-{day:02d}"

    m = re.search(
        r"(\d{4})-(\d{2})-(\d{2})",
        value
    )

    if m:
        return m.group(0)

    if "hoy" in value.lower():
        return colombia_date()

    if "mañana" in value.lower():
        return (
            colombia_now() + timedelta(days=1)
        ).strftime("%Y-%m-%d")

    return None


# =========================================================
# PARTIDO
# =========================================================

def split_match_name(match_text):

    if not match_text:
        return None, None

    patterns = [
        r"\s+-\s+",
        r"\s+–\s+",
        r"\s+—\s+",
        r"\s+vs\.?\s+",
        r"\s+v\.?\s+"
    ]

    for pattern in patterns:

        parts = re.split(
            pattern,
            match_text,
            maxsplit=1,
            flags=re.IGNORECASE
        )

        if len(parts) == 2:

            return (
                parts[0].strip(),
                parts[1].strip()
            )

    return None, None


# =========================================================
# DETECTAR ALERTA
# =========================================================

def is_bet_alert(text):

    lower = text.lower()

    keywords = [
        "trend",
        "🏆",
        "🆚",
        "🗓",
        "mercado:",
        "bet365:",
        "1xbet:",
        "888sport:",
        "pinnacle:",
        "ambos marcan",
        "btts",
        "más de",
        "menos de",
        "over",
        "under"
    ]

    count = sum(
        1
        for x in keywords
        if x in lower
    )

    return count >= 2


# =========================================================
# REGISTRAR SEÑAL
# =========================================================

def next_signal_id(signals):

    if not signals:
        return 1

    ids = []

    for s in signals:

        try:
            ids.append(
                int(s.get("id", 0))
            )
        except:
            pass

    return max(ids, default=0) + 1


def register_signal(text):

    signals = load_signals()

    for s in signals:

        if s.get("raw_message", "").strip() == text.strip():

            print("⚠️ Señal duplicada")
            return None

    signal = {

        "id": next_signal_id(signals),

        "registered_at":
            colombia_datetime(),

        "timezone":
            "America/Bogota",

        "league":
            extract(
                text,
                r"🏆\s*(.+)"
            ),

        "match":
            extract(
                text,
                r"🆚\s*(.+)"
            ),

        "date":
            extract(
                text,
                r"🗓\s*(.+)"
            ),

        "api_date":
            extract_signal_date(text),

        "strategy":
            extract_strategy(text),

        "odds":
            extract_odds(text),

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
# FOOTBALLDATA.IO
# =========================================================

def football_data_request(endpoint, params=None):

    if not FOOTBALLDATA_API_KEY:

        print(
            "❌ FOOTBALLDATA_API_KEY no configurada"
        )

        return None

    url = (
        "https://footballdata.io"
        + endpoint
    )

    headers = {
        "Authorization":
            f"Bearer {FOOTBALLDATA_API_KEY}",
        "Accept":
            "application/json"
    }

    try:

        r = requests.get(
            url,
            headers=headers,
            params=params or {},
            timeout=30
        )

        print(
            "FootballData:",
            r.status_code,
            r.url
        )

        if r.status_code != 200:

            print(
                "❌ API:",
                r.text[:1000]
            )

            return None

        return r.json()

    except Exception as e:

        print(
            "❌ Error FootballData:",
            e
        )

        return None


# =========================================================
# BUSCAR RESULTADOS DEL DÍA
# =========================================================

def get_results_for_date(date):

    data = football_data_request(
        "/api/v1/fixtures/results",
        {
            "date": date,
            "lang": "es"
        }
    )

    if not data:
        return []

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        inner = data.get("data")

        if isinstance(inner, dict):

            matches = inner.get("matches")

            if isinstance(matches, list):
                return matches

        if isinstance(inner, list):
            return inner

        matches = data.get("matches")

        if isinstance(matches, list):
            return matches

    return []


# =========================================================
# NORMALIZAR NOMBRE
# =========================================================

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
        name = name.replace(a, b)

    name = re.sub(
        r"[^a-z0-9 ]",
        "",
        name
    )

    return re.sub(
        r"\s+",
        " ",
        name
    ).strip()


# =========================================================
# BUSCAR PARTIDO
# =========================================================

def find_fixture_for_signal(signal):

    match_text = signal.get(
        "match",
        ""
    )

    home, away = split_match_name(
        match_text
    )

    if not home or not away:

        print(
            "⚠️ No pude separar:",
            match_text
        )

        return None

    date = signal.get(
        "api_date"
    )

    if not date:
        return None

    print(
        f"🔎 Buscando {home} vs {away} "
        f"en {date}"
    )

    matches = get_results_for_date(
        date
    )

    target_home = normalize_name(home)
    target_away = normalize_name(away)

    for fixture in matches:

        fh = fixture.get(
            "home_team",
            {}
        )

        fa = fixture.get(
            "away_team",
            {}
        )

        if isinstance(fh, dict):
            fixture_home = fh.get(
                "team_name",
                fh.get("name", "")
            )
        else:
            fixture_home = str(fh)

        if isinstance(fa, dict):
            fixture_away = fa.get(
                "team_name",
                fa.get("name", "")
            )
        else:
            fixture_away = str(fa)

        h = normalize_name(
            fixture_home
        )

        a = normalize_name(
            fixture_away
        )

        if (
            (
                target_home in h
                or h in target_home
            )
            and
            (
                target_away in a
                or a in target_away
            )
        ):

            print(
                "✅ PARTIDO ENCONTRADO:",
                fixture_home,
                "-",
                fixture_away
            )

            return fixture

    print(
        "⚠️ Partido no encontrado:",
        match_text
    )

    return None


# =========================================================
# EXTRAER MARCADOR
# =========================================================

def extract_score(fixture):

    home = None
    away = None

    possible_home = [
        "home_score",
        "home_goals"
    ]

    possible_away = [
        "away_score",
        "away_goals"
    ]

    for key in possible_home:

        if fixture.get(key) is not None:

            home = fixture.get(key)
            break

    for key in possible_away:

        if fixture.get(key) is not None:

            away = fixture.get(key)
            break

    score = fixture.get(
        "score",
        {}
    )

    if isinstance(score, dict):

        fulltime = score.get(
            "fulltime",
            score.get("ft", {})
        )

        if isinstance(fulltime, dict):

            if home is None:
                home = fulltime.get(
                    "home"
                )

            if away is None:
                away = fulltime.get(
                    "away"
                )

    return home, away


# =========================================================
# ESTADO
# =========================================================

def extract_status(fixture):

    status = fixture.get(
        "status",
        ""
    )

    if isinstance(status, dict):

        status = (
            status.get("status")
            or status.get("short")
            or status.get("name")
            or ""
        )

    return str(
        status
    ).lower()


def is_finished(status):

    finished_words = [
        "complete",
        "completed",
        "finalizado",
        "finished",
        "full time",
        "ft",
        "ended",
        "final"
    ]

    return any(
        word in status
        for word in finished_words
    )


# =========================================================
# EVALUAR
# =========================================================

def evaluate_strategy(
    strategy,
    home,
    away
):

    if home is None or away is None:
        return None

    try:
        home = int(home)
        away = int(away)
    except:
        return None

    total = home + away

    strategy = strategy.lower()

    if (
        "menos de 3.5" in strategy
        or "under 3.5" in strategy
    ):
        return total <= 3

    if (
        "menos de 2.5" in strategy
        or "under 2.5" in strategy
    ):
        return total <= 2

    if (
        "más de 3.5" in strategy
        or "over 3.5" in strategy
    ):
        return total >= 4

    if (
        "más de 2.5" in strategy
        or "over 2.5" in strategy
    ):
        return total >= 3

    if (
        "ambos marcan" in strategy
        or "btts" in strategy
    ):
        return home >= 1 and away >= 1

    if "victoria local" in strategy:
        return home > away

    if "victoria visitante" in strategy:
        return away > home

    return None


# =========================================================
# ACTUALIZAR RESULTADOS
# =========================================================

def update_pending_results():

    signals = load_signals()

    pending = [
        s for s in signals
        if s.get("result") == "PENDIENTE"
    ]

    print(
        f"⏳ Señales pendientes: {len(pending)}"
    )

    changed = False

    # Agrupar por fecha
    dates = {}

    for signal in pending:

        date = signal.get(
            "api_date"
        )

        if date:
            dates.setdefault(
                date,
                []
            ).append(signal)

    for date, date_signals in dates.items():

        print(
            f"📅 Consultando resultados: {date}"
        )

        matches = get_results_for_date(
            date
        )

        if not matches:
            continue

        for signal in date_signals:

            home, away = split_match_name(
                signal.get("match", "")
            )

            if not home or not away:
                continue

            target_home = normalize_name(home)
            target_away = normalize_name(away)

            found = None

            for fixture in matches:

                fh = fixture.get(
                    "home_team",
                    {}
                )

                fa = fixture.get(
                    "away_team",
                    {}
                )

                if isinstance(fh, dict):
                    fh = fh.get(
                        "team_name",
                        fh.get("name", "")
                    )

                if isinstance(fa, dict):
                    fa = fa.get(
                        "team_name",
                        fa.get("name", "")
                    )

                fh = normalize_name(
                    str(fh)
                )

                fa = normalize_name(
                    str(fa)
                )

                if (
                    (
                        target_home in fh
                        or fh in target_home
                    )
                    and
                    (
                        target_away in fa
                        or fa in target_away
                    )
                ):

                    found = fixture
                    break

            if not found:

                print(
                    "⚠️ No encontrado:",
                    signal.get("match")
                )

                continue

            fixture_id = (
                found.get("match_id")
                or found.get("id")
            )

            if fixture_id:

                signal["fixture_id"] = fixture_id

            status = extract_status(
                found
            )

            final_home, final_away = extract_score(
                found
            )

            print(
                f"⚽ {signal.get('match')} "
                f"→ {final_home}-{final_away} "
                f"| {status}"
            )

            signal[
                "live_home_goals"
            ] = final_home

            signal[
                "live_away_goals"
            ] = final_away

            signal[
                "live_status"
            ] = status

            changed = True

            # Solo resolver cuando haya terminado
            if not is_finished(status):
                continue

            won = evaluate_strategy(
                signal.get("strategy", ""),
                final_home,
                final_away
            )

            if won is None:

                print(
                    "⚠️ No se pudo evaluar:",
                    signal.get("strategy")
                )

                continue

            if won:

                signal["result"] = "GANADA"

            else:

                signal["result"] = "PERDIDA"

            signal[
                "final_home_goals"
            ] = final_home

            signal[
                "final_away_goals"
            ] = final_away

            signal[
                "result_at"
            ] = colombia_datetime()

            print(
                "🏁 RESULTADO:",
                signal["result"]
            )

    if changed:

        save_signals(signals)

        print(
            "💾 signals.json actualizado"
        )


# =========================================================
# ESTADÍSTICAS
# =========================================================

def calculate_stats(signals):

    won = 0
    lost = 0
    pending = 0
    profit = 0

    for s in signals:

        result = s.get(
            "result",
            "PENDIENTE"
        )

        odds = s.get(
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

    invested = finished * BET_AMOUNT

    roi = (
        profit / invested * 100
        if invested
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

    stats = calculate_stats(
        load_signals()
    )

    return f"""
🏆 APUESTASMURCIA
━━━━━━━━━━━━━━━━━━━━

🇨🇴 HORA COLOMBIA
{colombia_now().strftime("%d/%m/%Y %H:%M")}

📊 PANEL DE CONTROL

📥 Señales: {stats['total']}

⏳ Pendientes: {stats['pending']}

✅ Ganadas: {stats['won']}

❌ Perdidas: {stats['lost']}

━━━━━━━━━━━━━━━━━━━━

🎯 Efectividad:
{stats['effectiveness']:.1f}%

📈 ROI:
{stats['roi']:.1f}%

💰 Resultado:
${stats['profit']:,.0f} COP

💵 Apuesta:
${BET_AMOUNT:,.0f} COP
"""


def pendientes():

    signals = load_signals()

    pending = [
        s for s in signals
        if s.get("result") == "PENDIENTE"
    ]

    if not pending:

        return (
            "⏳ PENDIENTES\n\n"
            "🟢 No hay señales pendientes."
        )

    text = "⏳ SEÑALES PENDIENTES\n━━━━━━━━━━━━━━━━━━━━"

    for s in pending[-25:]:

        score = ""

        if (
            s.get("live_home_goals")
            is not None
            and
            s.get("live_away_goals")
            is not None
        ):

            score = (
                f"\n⚽ Marcador: "
                f"{s['live_home_goals']}-"
                f"{s['live_away_goals']}"
            )

        text += f"""

🆔 #{s.get('id')}

🏆 {s.get('league')}

⚽ {s.get('match')}

🎯 {s.get('strategy')}

💰 Cuota: {s.get('odds', 'N/D')}

⏳ PENDIENTE{score}

━━━━━━━━━━━━━━━━━━━━
"""

    return text


def estrategias():

    signals = load_signals()

    groups = {}

    for s in signals:

        strategy = s.get(
            "strategy",
            "SIN ESTRATEGIA"
        )

        groups.setdefault(
            strategy,
            []
        ).append(s)

    if not groups:
        return "🎯 No hay estrategias."

    text = "🎯 ESTRATEGIAS\n━━━━━━━━━━━━━━━━━━━━"

    for strategy, items in groups.items():

        stats = calculate_stats(items)

        text += f"""

🎯 {strategy}

📥 {stats['total']}
✅ {stats['won']}
❌ {stats['lost']}
⏳ {stats['pending']}

🎯 Efectividad:
{stats['effectiveness']:.1f}%

📈 ROI:
{stats['roi']:.1f}%

💰 Resultado:
${stats['profit']:,.0f} COP

━━━━━━━━━━━━━━━━━━━━
"""

    return text


def ganancias():

    stats = calculate_stats(
        load_signals()
    )

    return f"""
💰 GANANCIAS
━━━━━━━━━━━━━━━━━━━━

💵 Apuesta:
${BET_AMOUNT:,.0f} COP

💰 Resultado:
${stats['profit']:,.0f} COP

📈 ROI:
{stats['roi']:.1f}%

🎯 Efectividad:
{stats['effectiveness']:.1f}%
"""


def estadisticas():

    stats = calculate_stats(
        load_signals()
    )

    return f"""
📈 ESTADÍSTICAS
━━━━━━━━━━━━━━━━━━━━

📥 Total: {stats['total']}

✅ Ganadas: {stats['won']}

❌ Perdidas: {stats['lost']}

⏳ Pendientes: {stats['pending']}

🎯 Efectividad:
{stats['effectiveness']:.1f}%

📈 ROI:
{stats['roi']:.1f}%

💰 Resultado:
${stats['profit']:,.0f} COP
"""


def configuracion():

    api = (
        "🟢 CONFIGURADA"
        if FOOTBALLDATA_API_KEY
        else
        "🔴 NO CONFIGURADA"
    )

    return f"""
⚙️ CONFIGURACIÓN
━━━━━━━━━━━━━━━━━━━━

🇨🇴 Zona horaria:
America/Bogota

💵 Apuesta:
${BET_AMOUNT:,.0f} COP

🤖 Resultados:
FootballData.io

🔑 API:
{api}

🔄 Ejecución:
Cada 5 minutos
"""


# =========================================================
# CALLBACKS
# =========================================================

def process_callback(callback):

    answer_callback(
        callback.get("id")
    )

    message = callback.get(
        "message"
    )

    if not message:
        return

    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

    data = callback.get(
        "data",
        ""
    )

    pages = {

        "inicio":
            (
                dashboard(),
                main_keyboard()
            ),

        "rendimiento":
            (
                dashboard(),
                back_keyboard()
            ),

        "estrategias":
            (
                estrategias(),
                back_keyboard()
            ),

        "pendientes":
            (
                pendientes(),
                back_keyboard()
            ),

        "ganancias":
            (
                ganancias(),
                back_keyboard()
            ),

        "estadisticas":
            (
                estadisticas(),
                back_keyboard()
            ),

        "configuracion":
            (
                configuracion(),
                back_keyboard()
            )
    }

    if data in pages:

        text, keyboard = pages[data]

        edit_message(
            chat_id,
            message_id,
            text,
            keyboard
        )


# =========================================================
# MENSAJES
# =========================================================

def process_message(message):

    chat_id = message.get(
        "chat",
        {}
    ).get("id")

    text = message.get(
        "text",
        ""
    ).strip()

    if not chat_id or not text:
        return

    if text in ["/start", "/panel"]:

        send_message(
            chat_id,
            dashboard(),
            main_keyboard()
        )

        return

    if text == "/pendientes":

        send_message(
            chat_id,
            pendientes(),
            back_keyboard()
        )

        return

    if text == "/estrategias":

        send_message(
            chat_id,
            estrategias(),
            back_keyboard()
        )

        return

    if text.startswith("/"):

        return

    if not is_bet_alert(text):

        return

    signal = register_signal(text)

    if not signal:
        return

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

💰 Cuota:
{signal['odds']}

⏳ ESTADO:
PENDIENTE

🇨🇴 {signal['registered_at']}

━━━━━━━━━━━━━━━━━━━━

🤖 El bot comprobará
automáticamente el resultado.
"""
    )


# =========================================================
# TELEGRAM UPDATES
# =========================================================

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

        result = r.json()

        if not result.get("ok"):

            print(
                "❌ getUpdates:",
                result
            )

            return []

        return result.get(
            "result",
            []
        )

    except Exception as e:

        print(
            "❌ Telegram:",
            e
        )

        return []


# =========================================================
# MAIN
# =========================================================

def main():

    print("=" * 45)
    print("       APUESTASMURCIA BOT")
    print("=" * 45)

    print(
        "🇨🇴 Hora:",
        colombia_datetime()
    )

    print(
        "🔑 FootballData:",
        "CONFIGURADA"
        if FOOTBALLDATA_API_KEY
        else "NO CONFIGURADA"
    )

    # -----------------------------------------
    # ACTUALIZAR RESULTADOS
    # -----------------------------------------

    update_pending_results()

    # -----------------------------------------
    # TELEGRAM
    # -----------------------------------------

    offset = load_offset()

    updates = get_updates(
        offset
    )

    print(
        "📨 Updates:",
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
                "❌ Error update:",
                e
            )

        if update_id is not None:

            save_offset(
                update_id + 1
            )

    print("=" * 45)
    print("Ejecución terminada.")
    print("=" * 45)


if __name__ == "__main__":
    main()