import os
import re
import json
import time
import requests
from datetime import datetime, timezone

# ============================================================
# CONFIGURACION
# ============================================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

DATA_FILE = "signals.json"


# ============================================================
# BASE DE DATOS
# ============================================================

def load_signals():

    if not os.path.exists(DATA_FILE):
        return []

    try:

        with open(DATA_FILE, "r", encoding="utf-8") as f:

            return json.load(f)

    except Exception as e:

        print("Error leyendo señales:", e)

        return []


def save_signals(signals):

    with open(DATA_FILE, "w", encoding="utf-8") as f:

        json.dump(
            signals,
            f,
            ensure_ascii=False,
            indent=2
        )


# ============================================================
# TELEGRAM
# ============================================================

def send_message(chat_id, text):

    try:

        response = requests.post(

            f"{TELEGRAM_URL}/sendMessage",

            data={
                "chat_id": chat_id,
                "text": text
            },

            timeout=30
        )

        if not response.ok:

            print(
                "Error Telegram:",
                response.text
            )

        return response.ok

    except Exception as e:

        print(
            "Error enviando Telegram:",
            e
        )

        return False


# ============================================================
# EXTRAER LIGA
# ============================================================

def extract_league(text):

    match = re.search(
        r"🏆\s*(.+)",
        text
    )

    if match:

        return match.group(1).strip()

    return "No identificada"


# ============================================================
# EXTRAER PARTIDO
# ============================================================

def extract_match(text):

    match = re.search(
        r"🆚\s*(.+?)\s*-\s*(.+)",
        text
    )

    if match:

        home = match.group(1).strip()

        away = match.group(2).strip()

        return f"{home} vs {away}"

    return "No identificado"


# ============================================================
# EXTRAER FECHA
# ============================================================

def extract_datetime(text):

    match = re.search(
        r"🗓\s*(.+)",
        text
    )

    if match:

        return match.group(1).strip()

    return "No identificada"


# ============================================================
# SUCCESS PERCENTAGE
# ============================================================

def extract_success(text):

    match = re.search(
        r"Success Percentage:\s*([\d.,]+)\s*%",
        text,
        re.IGNORECASE
    )

    if match:

        return float(
            match.group(1).replace(",", ".")
        )

    return None


# ============================================================
# ROI
# ============================================================

def extract_roi(text):

    match = re.search(
        r"ROI:\s*([\d.,+-]+)\s*%",
        text,
        re.IGNORECASE
    )

    if match:

        return float(
            match.group(1).replace(",", ".")
        )

    return None


# ============================================================
# PICKS
# ============================================================

def extract_picks(text):

    match = re.search(
        r"picks:\s*(\d+)",
        text,
        re.IGNORECASE
    )

    if match:

        return int(
            match.group(1)
        )

    return None


# ============================================================
# RANKING
# ============================================================

def extract_ranking(text):

    match = re.search(
        r"Posición en el ranking:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1).strip()

    return "No identificado"


# ============================================================
# RESULTADO DESEADO
# ============================================================

def extract_target(text):

    match = re.search(
        r"Resultado deseado:\s*(.+)",
        text,
        re.IGNORECASE
    )

    if match:

        target = match.group(1).strip()

        if target:

            return target

    return "SIN ESTRATEGIA"


# ============================================================
# ESTRATEGIA
# ============================================================
#
# IMPORTANTE:
#
# NO HAY UNA LISTA FIJA.
#
# CUALQUIER TEXTO QUE APAREZCA DESPUES DE
#
# Resultado deseado:
#
# SE GUARDA AUTOMATICAMENTE COMO ESTRATEGIA.
#
# ============================================================

def detect_strategy(target):

    if target:

        return target.strip()

    return "SIN ESTRATEGIA"


# ============================================================
# CUOTA PRINCIPAL
# ============================================================

def extract_main_odds(text):

    match = re.search(
        r"bet365:\s*([\d.,]+)",
        text,
        re.IGNORECASE
    )

    if match:

        return float(
            match.group(1).replace(",", ".")
        )

    return None


# ============================================================
# CUOTAS 1X2
# ============================================================

def extract_1x2(text):

    match = re.search(
        r"1\s+([\d.,]+)\s+X\s+([\d.,]+)\s+2\s+([\d.,]+)",
        text
    )

    if not match:

        return None

    return {

        "home": float(
            match.group(1).replace(",", ".")
        ),

        "draw": float(
            match.group(2).replace(",", ".")
        ),

        "away": float(
            match.group(3).replace(",", ".")
        )
    }


# ============================================================
# OVER UNDER
# ============================================================

def extract_over_under(text):

    match = re.search(
        r"\+2\.5\s+([\d.,]+)\s+-2\.5\s+([\d.,]+)",
        text
    )

    if not match:

        return None

    return {

        "over25": float(
            match.group(1).replace(",", ".")
        ),

        "under25": float(
            match.group(2).replace(",", ".")
        )
    }


# ============================================================
# BTTS
# ============================================================

def extract_btts(text):

    match = re.search(
        r"SI\s+([\d.,]+)\s+NO\s+([\d.,]+)",
        text
    )

    if not match:

        return None

    return {

        "yes": float(
            match.group(1).replace(",", ".")
        ),

        "no": float(
            match.group(2).replace(",", ".")
        )
    }


# ============================================================
# REGISTRAR SEÑAL
# ============================================================

def register_signal(text):

    signals = load_signals()

    league = extract_league(text)

    match = extract_match(text)

    event_datetime = extract_datetime(text)

    success = extract_success(text)

    roi = extract_roi(text)

    picks = extract_picks(text)

    ranking = extract_ranking(text)

    target = extract_target(text)

    strategy = detect_strategy(target)

    odds = extract_main_odds(text)

    odds_1x2 = extract_1x2(text)

    odds_goals = extract_over_under(text)

    odds_btts = extract_btts(text)

    signal = {

        "id": len(signals) + 1,

        "registered_at":
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "league": league,

        "match": match,

        "event_datetime": event_datetime,

        "strategy": strategy,

        "target": target,

        "odds": odds,

        "success_percentage": success,

        "betmines_roi": roi,

        "picks": picks,

        "ranking": ranking,

        "odds_1x2": odds_1x2,

        "odds_goals": odds_goals,

        "odds_btts": odds_btts,

        "result": "PENDIENTE",

        "raw_message": text
    }

    signals.append(signal)

    save_signals(signals)

    return signal


# ============================================================
# MOSTRAR SEÑAL
# ============================================================

def format_signal(signal):

    if signal["odds"] is not None:

        odds = f"{signal['odds']:.2f}"

    else:

        odds = "N/D"


    if signal["success_percentage"] is not None:

        success = (
            f"{signal['success_percentage']:.1f}%"
        )

    else:

        success = "N/D"


    if signal["betmines_roi"] is not None:

        roi = (
            f"{signal['betmines_roi']:.1f}%"
        )

    else:

        roi = "N/D"


    picks = (
        signal["picks"]
        if signal["picks"] is not None
        else "N/D"
    )


    return f"""
SEÑAL REGISTRADA

ID: #{signal['id']}

LIGA:
{signal['league']}

PARTIDO:
{signal['match']}

FECHA:
{signal['event_datetime']}

ESTRATEGIA:
{signal['strategy']}

RESULTADO DESEADO:
{signal['target']}

CUOTA:
{odds}

SUCCESS BETMINES:
{success}

ROI BETMINES:
{roi}

PICKS:
{picks}

RANKING:
{signal['ranking']}

ESTADO:
PENDIENTE

Comandos:

/panel
/estrategias
/pendientes
/hoy
"""


# ============================================================
# PANEL
# ============================================================

def panel():

    signals = load_signals()

    if not signals:

        return "No hay señales registradas."


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
PANEL DE RENDIMIENTO

SEÑALES: {total}

GANADAS: {won}

PERDIDAS: {lost}

PENDIENTES: {pending}

EFECTIVIDAD:
{effectiveness:.1f}%

BENEFICIO:
{profit:+.2f} unidades

ROI:
{roi:+.1f}%
"""


# ============================================================
# ESTRATEGIAS
# ============================================================

def strategies_panel():

    signals = load_signals()

    if not signals:

        return "No hay señales registradas."


    strategies = {}


    for signal in signals:

        strategy = signal.get(
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


        strategies[strategy]["total"] += 1


        if signal["result"] == "GANADA":

            strategies[strategy]["won"] += 1

            odds = signal.get("odds")

            if odds:

                strategies[strategy]["profit"] += (
                    odds - 1
                )

            else:

                strategies[strategy]["profit"] += 1


        elif signal["result"] == "PERDIDA":

            strategies[strategy]["lost"] += 1

            strategies[strategy]["profit"] -= 1


        else:

            strategies[strategy]["pending"] += 1


    output = "RENDIMIENTO POR ESTRATEGIA\n\n"


    ordered = sorted(

        strategies.items(),

        key=lambda x: x[1]["total"],

        reverse=True

    )


    for strategy, data in ordered:

        finished = (
            data["won"]
            + data["lost"]
        )


        if finished > 0:

            percentage = (
                data["won"]
                / finished
            ) * 100

        else:

            percentage = 0


        output += (

            f"ESTRATEGIA: {strategy}\n"

            f"Señales: {data['total']}\n"

            f"Ganadas: {data['won']}\n"

            f"Perdidas: {data['lost']}\n"

            f"Pendientes: {data['pending']}\n"

            f"Efectividad: "
            f"{percentage:.1f}%\n"

            f"Beneficio: "
            f"{data['profit']:+.2f}\n\n"

        )


    return output


# ============================================================
# PENDIENTES
# ============================================================

def pending_panel():

    signals = load_signals()


    pending = [

        s

        for s in signals

        if s["result"] == "PENDIENTE"

    ]


    if not pending:

        return "No hay señales pendientes."


    output = "SEÑALES PENDIENTES\n\n"


    for signal in pending[-20:]:

        odds = signal.get("odds")


        if odds:

            odds_text = f"{odds:.2f}"

        else:

            odds_text = "N/D"


        output += (

            f"#{signal['id']}\n"

            f"{signal['match']}\n"

            f"Estrategia: "
            f"{signal['strategy']}\n"

            f"Cuota: {odds_text}\n"

            f"{signal['event_datetime']}\n\n"

        )


    return output


# ============================================================
# ACTUALIZAR RESULTADO
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
# PROCESAR MENSAJE
# ============================================================

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


    if not text:

        return


    # START

    if text == "/start":

        send_message(

            chat_id,

            """
APUESTASMURCIA BOT

BOT ACTIVO.

Envíame cualquier alerta
copiada de BetMines.

El bot reconoce automaticamente
cualquier estrategia.

Comandos:

/panel
/estrategias
/pendientes
/hoy

Resultados:

/ganada ID
/perdida ID
"""

        )

        return


    # PANEL

    if text == "/panel":

        send_message(
            chat_id,
            panel()
        )

        return


    # ESTRATEGIAS

    if text == "/estrategias":

        send_message(
            chat_id,
            strategies_panel()
        )

        return


    # PENDIENTES

    if text == "/pendientes":

        send_message(
            chat_id,
            pending_panel()
        )

        return


    # HOY

    if text == "/hoy":

        today = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d")


        signals = load_signals()


        today_signals = [

            s

            for s in signals

            if s["registered_at"].startswith(today)

        ]


        if not today_signals:

            send_message(
                chat_id,
                "No hay señales registradas hoy."
            )

            return


        output = "SEÑALES DE HOY\n\n"


        for signal in today_signals:

            output += (

                f"#{signal['id']}\n"

                f"{signal['match']}\n"

                f"Estrategia: "
                f"{signal['strategy']}\n"

                f"Cuota: "
                f"{signal['odds'] or 'N/D'}\n"

                f"Estado: "
                f"{signal['result']}\n\n"

            )


        send_message(
            chat_id,
            output
        )

        return


    # GANADA

    match = re.match(
        r"^/ganada\s+(\d+)$",
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

                f"Señal #{signal_id} "
                f"marcada como GANADA."

            )

        else:

            send_message(
                chat_id,
                "No existe esa señal."
            )


        return


    # PERDIDA

    match = re.match(
        r"^/perdida\s+(\d+)$",
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

                f"Señal #{signal_id} "
                f"marcada como PERDIDA."

            )

        else:

            send_message(
                chat_id,
                "No existe esa señal."
            )


        return


    # ========================================================
    # CUALQUIER OTRO MENSAJE
    # SE CONSIDERA UNA ALERTA DE BETMINES
    # ========================================================

    signal = register_signal(text)


    send_message(

        chat_id,

        format_signal(signal)

    )


# ============================================================
# INICIAR BOT
# ============================================================

def run_bot():

    print("")
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
                "Error polling:",
                e
            )

            time.sleep(5)


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == "__main__":

    run_bot()