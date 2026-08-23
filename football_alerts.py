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
FOOTBALLDATA_API_KEY = os.environ.get(
    "FOOTBALLDATA_API_KEY",
    ""
)

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

SIGNALS_FILE = "signals.json"
OFFSET_FILE = "telegram_offset.json"

BET_AMOUNT = 5000

COLOMBIA_TZ = ZoneInfo("America/Bogota")


# =========================================================
# HORA COLOMBIA
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

        response = requests.post(
            f"{TELEGRAM_URL}/{method}",
            data=data or {},
            timeout=30
        )

        result = response.json()

        print(
            f"Telegram {method}: {result.get('ok')}"
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
            "ok": False
        }


def send_message(chat_id, text, keyboard=None):

    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard is not None:

        data["reply_markup"] = json.dumps({
            "inline_keyboard": keyboard
        }, ensure_ascii=False)

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

        data["reply_markup"] = json.dumps({
            "inline_keyboard": keyboard
        }, ensure_ascii=False)

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

        return data if isinstance(data, list) else []

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

            return json.load(file).get("offset")

    except Exception:

        return None


def save_offset(offset):

    try:

        with open(
            OFFSET_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                {"offset": offset},
                file
            )

        return True

    except Exception:

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

    return [[
        {
            "text": "⬅️ Volver al panel",
            "callback_data": "inicio"
        }
    ]]


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

def extract(text, patterns, default="No identificado"):

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

    lower = text.lower()

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

    # Menos de 3.5
    if (
        "menos de 3.5" in lower
        or "under 3.5" in lower
    ):
        return "Menos de 3.5 goles"

    # Menos de 2.5
    if (
        "menos de 2.5" in lower
        or "under 2.5" in lower
    ):
        return "Menos de 2.5 goles"

    # Más de 3.5
    if (
        "más de 3.5" in lower
        or "over 3.5" in lower
    ):
        return "Más de 3.5 goles"

    # Más de 2.5
    if (
        "más de 2.5" in lower
        or "over 2.5" in lower
    ):
        return "Más de 2.5 goles"

    # BTTS
    if (
        "ambos marcan" in lower
        or "btts" in lower
    ):
        return "Ambos Marcan"

    # Empate primer tiempo
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

    # Formato:
    # 🗓 lun, 24 ago 2026 23:00

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

    match = re.search(
        r"(\d{1,2})\s+"
        r"(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)"
        r"\s+(\d{4})",
        value.lower()
    )

    if match:

        day = int(match.group(1))
        month = months[match.group(2)]
        year = int(match.group(3))

        return (
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

    # Formatos numéricos

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

        if match:

            groups = match.groups()

            if len(groups[0]) == 4:

                year, month, day = groups

            else:

                day, month, year = groups

            return (
                f"{year}-"
                f"{month.zfill(2)}-"
                f"{day.zfill(2)}"
            )

    if "mañana" in value.lower():

        return (
            colombia_now() +
            timedelta(days=1)
        ).strftime("%Y-%m-%d")

    if "hoy" in value.lower():

        return colombia_date()

    return None


# =========================================================
# PARTIDO
# =========================================================

def split_match_name(match_text):

    if not match_text:
        return None, None

    separators = [
        r"\s+vs\.?\s+",
        r"\s+v\.?\s+",
        r"\s+-\s+",
        r"\s+–\s+",
        r"\s+—\s+",
        r"\s+🆚\s+"
    ]

    for separator in separators:

        parts = re.split(
            separator,
            match_text.strip(),
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

    if not text:
        return False

    if text.startswith("/"):
        return False

    lower = text.lower()

    keywords = [
        "trend",
        "🏆",
        "🆚",
        "🗓",
        "liga:",
        "partido:",
        "mercado:",
        "resultado deseado:",
        "bet365:",
        "1xbet:",
        "888sport:",
        "pinnacle:",
        "betmines",
        "ambos marcan",
        "btts",
        "más de",
        "menos de",
        "over",
        "under",
        "empate"
    ]

    matches = sum(
        1
        for keyword in keywords
        if keyword in lower
    )

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
                int(signal.get("id", 0))
            )

        except Exception:
            pass

    return max(ids, default=0) + 1


def register_signal(text):

    signals = load_signals()

    for signal in signals:

        if signal.get(
            "raw_message",
            ""
        ).strip() == text.strip():

            print("⚠️ Señal duplicada.")
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

def football_data_request(
    endpoint,
    params=None
):

    if not FOOTBALLDATA_API_KEY:

        print(
            "❌ FOOTBALLDATA_API_KEY no configurada"
        )

        return None

    try:

        response = requests.get(
            f"https://api.footballdata.io{endpoint}",
            headers={
                "Authorization":
                    f"Bearer {FOOTBALLDATA_API_KEY}",
                "Accept":
                    "application/json"
            },
            params=params or {},
            timeout=30
        )

        print(
            "FootballData:",
            endpoint,
            "HTTP",
            response.status_code
        )

        if response.status_code != 200:

            print(
                "❌ Respuesta API:",
                response.text[:1000]
            )

            return None

        return response.json()

    except Exception as e:

        print(
            "❌ Error FootballData:",
            e
        )

        return None


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

        date = colombia_date()

    print(
        "🔎 Buscando:",
        home,
        "vs",
        away,
        date
    )

    # La búsqueda se deja centralizada
    # para poder adaptarla al endpoint
    # exacto disponible en tu cuenta.

    data = football_data_request(
        "/fixtures",
        {
            "date": date
        }
    )

    if not data:

        return None

    # Algunas APIs devuelven directamente
    # una lista y otras dentro de data.

    if isinstance(data, list):

        fixtures = data

    elif isinstance(data, dict):

        fixtures = (
            data.get("data")
            or data.get("fixtures")
            or data.get("response")
            or []
        )

    else:

        fixtures = []

    target_home = home.lower()
    target_away = away.lower()

    for fixture in fixtures:

        fixture_home = ""
        fixture_away = ""

        teams = fixture.get(
            "teams",
            {}
        )

        if isinstance(teams, dict):

            fixture_home = str(
                teams.get("home", {}).get(
                    "name",
                    ""
                )
            )

            fixture_away = str(
                teams.get("away", {}).get(
                    "name",
                    ""
                )
            )

        fixture_home = fixture_home.lower()
        fixture_away = fixture_away.lower()

        if (
            target_home in fixture_home
            and
            target_away in fixture_away
        ):

            print(
                "✅ Partido encontrado"
            )

            return fixture

    print(
        "⚠️ Partido no encontrado:",
        match_text
    )

    return None


# =========================================================
# EVALUAR ESTRATEGIA
# =========================================================

def evaluate_strategy(
    strategy,
    final_home,
    final_away,
    halftime_home=None,
    halftime_away=None
):

    if (
        final_home is None
        or final_away is None
    ):
        return None

    strategy = strategy.lower()

    total_goals = (
        final_home +
        final_away
    )

    # -----------------------------------------------------
    # MENOS DE 3.5
    # -----------------------------------------------------

    if (
        "menos de 3.5" in strategy
        or "under 3.5" in strategy
    ):

        return total_goals < 3.5

    # -----------------------------------------------------
    # MENOS DE 2.5
    # -----------------------------------------------------

    if (
        "menos de 2.5" in strategy
        or "under 2.5" in strategy
    ):

        return total_goals < 2.5

    # -----------------------------------------------------
    # MÁS DE 3.5
    # -----------------------------------------------------

    if (
        "más de 3.5" in strategy
        or "over 3.5" in strategy
    ):

        return total_goals >= 4

    # -----------------------------------------------------
    # MÁS DE 2.5
    # -----------------------------------------------------

    if (
        "más de 2.5" in strategy
        or "over 2.5" in strategy
    ):

        return total_goals >= 3

    # -----------------------------------------------------
    # AMBOS MARCAN
    # -----------------------------------------------------

    if (
        "ambos marcan" in strategy
        or "btts" in strategy
    ):

        return (
            final_home >= 1
            and
            final_away >= 1
        )

    # -----------------------------------------------------
    # EMPATE PRIMER TIEMPO
    # -----------------------------------------------------

    if "empate primer tiempo" in strategy:

        if (
            halftime_home is None
            or halftime_away is None
        ):
            return None

        return halftime_home == halftime_away

    # -----------------------------------------------------
    # VICTORIA LOCAL
    # -----------------------------------------------------

    if "victoria local" in strategy:

        return final_home > final_away

    # -----------------------------------------------------
    # VICTORIA VISITANTE
    # -----------------------------------------------------

    if "victoria visitante" in strategy:

        return final_away > final_home

    return None


# =========================================================
# ACTUALIZAR RESULTADOS
# =========================================================

def update_pending_results():

    signals = load_signals()

    pending = [
        s for s in signals
        if s.get(
            "result",
            "PENDIENTE"
        ) == "PENDIENTE"
    ]

    print(
        "⏳ Pendientes:",
        len(pending)
    )

    changed = False

    for signal in pending:

        try:

            fixture = None

            if not signal.get(
                "fixture_id"
            ):

                fixture = find_fixture_for_signal(
                    signal
                )

                if not fixture:
                    continue

                fixture_id = (
                    fixture.get("id")
                    or
                    fixture.get(
                        "fixture_id"
                    )
                )

                if fixture_id:
                    signal[
                        "fixture_id"
                    ] = fixture_id
                    changed = True

            else:

                fixture_id = signal[
                    "fixture_id"
                ]

            if not fixture_id:
                continue

            # -------------------------------------------------
            # CONSULTAR PARTIDO
            # -------------------------------------------------

            data = football_data_request(
                f"/fixtures/{fixture_id}"
            )

            if not data:

                continue

            if isinstance(data, dict):

                fixture = (
                    data.get("data")
                    or data.get("fixture")
                    or data
                )

            # -------------------------------------------------
            # EXTRAER MARCADOR
            # -------------------------------------------------

            home_goals = None
            away_goals = None
            ht_home = None
            ht_away = None

            score = fixture.get(
                "score",
                {}
            )

            if isinstance(score, dict):

                fulltime = score.get(
                    "fulltime",
                    {}
                )

                halftime = score.get(
                    "halftime",
                    {}
                )

                if isinstance(
                    fulltime,
                    dict
                ):

                    home_goals = (
                        fulltime.get("home")
                    )

                    away_goals = (
                        fulltime.get("away")
                    )

                if isinstance(
                    halftime,
                    dict
                ):

                    ht_home = (
                        halftime.get("home")
                    )

                    ht_away = (
                        halftime.get("away")
                    )

            # Formato alternativo

            if home_goals is None:

                home_goals = fixture.get(
                    "home_score"
                )

            if away_goals is None:

                away_goals = fixture.get(
                    "away_score"
                )

            # -------------------------------------------------
            # ESTADO
            # -------------------------------------------------

            status = str(
                fixture.get(
                    "status",
                    ""
                )
            ).upper()

            if isinstance(
                fixture.get("status"),
                dict
            ):

                status = str(
                    fixture[
                        "status"
                    ].get(
                        "short",
                        ""
                    )
                ).upper()

            print(
                f"⚽ {signal.get('match')} "
                f"| {home_goals}-{away_goals} "
                f"| {status}"
            )

            # Guardar información actual

            signal[
                "live_home_goals"
            ] = home_goals

            signal[
                "live_away_goals"
            ] = away_goals

            signal[
                "live_status"
            ] = status

            signal[
                "halftime_home"
            ] = ht_home

            signal[
                "halftime_away"
            ] = ht_away

            changed = True

            # -------------------------------------------------
            # DETERMINAR SI TERMINÓ
            # -------------------------------------------------

            finished = status in [
                "FT",
                "AET",
                "PEN",
                "FINISHED",
                "COMPLETED"
            ]

            if not finished:

                continue

            # -------------------------------------------------
            # EVALUAR
            # -------------------------------------------------

            won = evaluate_strategy(
                signal.get(
                    "strategy",
                    ""
                ),
                home_goals,
                away_goals,
                ht_home,
                ht_away
            )

            if won is None:

                print(
                    "⚠️ No se pudo evaluar:",
                    signal.get("strategy")
                )

                continue

            signal[
                "result"
            ] = (
                "GANADA"
                if won
                else
                "PERDIDA"
            )

            signal[
                "result_at"
            ] = colombia_datetime()

            signal[
                "final_home_goals"
            ] = home_goals

            signal[
                "final_away_goals"
            ] = away_goals

            print(
                "🏁",
                signal["result"],
                signal.get("match"),
                f"{home_goals}-{away_goals}"
            )

        except Exception as e:

            print(
                "❌ Error procesando:",
                signal.get("match"),
                e
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

    invested = (
        finished *
        BET_AMOUNT
    )

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
"""


def rendimiento():

    return dashboard()


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

        return "🎯 No hay estrategias registradas."

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

    text = (
        "⏳ SEÑALES PENDIENTES\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    for signal in pending[:25]:

        score = ""

        if (
            signal.get(
                "live_home_goals"
            ) is not None
            and
            signal.get(
                "live_away_goals"
            ) is not None
        ):

            score = (
                f"\n⚽ Marcador: "
                f"{signal['live_home_goals']}-"
                f"{signal['live_away_goals']}"
            )

        text += f"""

🆔 #{signal.get('id')}

🏆 {signal.get('league')}

⚽ {signal.get('match')}

🎯 {signal.get('strategy')}

💰 Cuota: {signal.get('odds', 'N/D')}{score}

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

💵 Apuesta
${BET_AMOUNT:,.0f} COP

💰 Resultado
${stats['profit']:,.0f} COP

📈 ROI
{stats['roi']:.1f}%

🎯 Efectividad
{stats['effectiveness']:.1f}%
"""


def estadisticas():

    stats = calculate_stats(
        load_signals()
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

🎯 Efectividad
{stats['effectiveness']:.1f}%

📈 ROI
{stats['roi']:.1f}%

💰 Resultado
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

🇨🇴 America/Bogota

💵 Apuesta:
${BET_AMOUNT:,.0f} COP

🤖 Resultados:
FootballData

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

    chat_id = message[
        "chat"
    ][
        "id"
    ]

    message_id = message[
        "message_id"
    ]

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
                rendimiento(),
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

    if text == "/start" or text == "/panel":

        send_message(
            chat_id,
            dashboard(),
            main_keyboard()
        )

        return

    if text == "/estrategias":

        send_message(
            chat_id,
            estrategias(),
            back_keyboard()
        )

        return

    if text == "/pendientes":

        send_message(
            chat_id,
            pendientes(),
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

💰 Cuota: {signal['odds']}

⏳ ESTADO: PENDIENTE

🇨🇴 {signal['registered_at']}

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
        "===================================="
    )

    print(
        "Hora:",
        colombia_datetime()
    )

    print(
        "API resultados:",
        "CONFIGURADA"
        if FOOTBALLDATA_API_KEY
        else "NO CONFIGURADA"
    )

    # Actualizar resultados
    update_pending_results()

    # Telegram
    offset = load_offset()

    updates = get_updates(
        offset
    )

    print(
        "Mensajes:",
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