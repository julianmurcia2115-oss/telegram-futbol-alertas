import os
import json
import re
import time
import requests
from datetime import datetime, timezone, timedelta

# ============================================================
# CONFIGURACIÓN
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_FOOTBALL_KEY = os.getenv("API_FOOTBALL_KEY")

SIGNALS_FILE = "signals.json"
STATE_FILE = "bot_state.json"

STAKE = 5000
COLOMBIA_TZ = timezone(timedelta(hours=-5))
API_URL = "https://v3.football.api-sports.io"

POLL_SECONDS = 20
RESULTADOS_INTERVALO = 900  # revisar resultados cada 15 minutos (solo modo VPS)

MESES_ES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dic": 12
}

if not TELEGRAM_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN NO CONFIGURADO")
    raise SystemExit(1)
if not CHAT_ID:
    print("❌ TELEGRAM_CHAT_ID NO CONFIGURADO")
    raise SystemExit(1)
if not API_FOOTBALL_KEY:
    print("❌ API_FOOTBALL_KEY NO CONFIGURADO")
    raise SystemExit(1)

print("====================================")
print("⚽ FOOTBALL ALERTS")
print("====================================")


# ============================================================
# JSON
# ============================================================
def cargar_json(archivo, defecto):
    try:
        if not os.path.exists(archivo):
            return defecto
        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error leyendo {archivo}: {e}")
        return defecto


def guardar_json(archivo, datos):
    temporal = archivo + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    os.replace(temporal, archivo)


def cargar_apuestas():
    datos = cargar_json(SIGNALS_FILE, [])
    if isinstance(datos, list):
        return datos
    if isinstance(datos, dict):
        if "signals" in datos:
            return datos["signals"]
        if "apuestas" in datos:
            return datos["apuestas"]
    return []


def guardar_apuestas(apuestas):
    guardar_json(SIGNALS_FILE, apuestas)


def cargar_estado():
    estado = cargar_json(STATE_FILE, {})
    if not isinstance(estado, dict):
        estado = {}
    return estado


def guardar_estado(estado):
    guardar_json(STATE_FILE, estado)


# ============================================================
# TELEGRAM
# ============================================================
def telegram_api(method, data=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    try:
        response = requests.post(url, data=data or {}, timeout=30)
        if response.status_code == 200:
            return response.json()
        print(f"❌ Telegram {response.status_code}: {response.text}")
    except Exception as e:
        print(f"❌ Error Telegram: {e}")
    return None


def enviar(mensaje, chat_id=None, botones=None):
    if chat_id is None:
        chat_id = CHAT_ID
    datos = {"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}
    if botones:
        datos["reply_markup"] = json.dumps(botones, ensure_ascii=False)
    return telegram_api("sendMessage", datos)


# ============================================================
# UTILIDADES
# ============================================================
def ahora_colombia():
    return datetime.now(COLOMBIA_TZ).strftime("%Y-%m-%d %H:%M:%S")


def normalizar(texto):
    if not texto:
        return ""
    texto = str(texto).lower()
    reemplazos = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)
    texto = re.sub(r"[^a-z0-9\s+.-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def nombres_equivalentes(nombre1, nombre2):
    a = normalizar(nombre1)
    b = normalizar(nombre2)
    if not a or not b:
        return False
    if a == b:
        return True
    palabras_a = set(a.split())
    palabras_b = set(b.split())
    interseccion = palabras_a & palabras_b
    minimo = min(len(palabras_a), len(palabras_b))
    if minimo > 0 and (len(interseccion) / minimo) >= 0.6:
        return True
    return a in b or b in a


def parsear_fecha_partido(texto_fecha):
    """Convierte '🗓 mar, 01 sept 2026 07:00' -> datetime(2026,9,1)."""
    if not texto_fecha:
        return None
    t = normalizar(texto_fecha)
    match = re.search(r"(\d{1,2})\s+([a-z]+)\.?\s+(\d{4})", t)
    if not match:
        return None
    dia = int(match.group(1))
    mes_txt = match.group(2)[:4]
    mes = None
    for abrev, numero in MESES_ES.items():
        if mes_txt.startswith(abrev):
            mes = numero
            break
    if mes is None:
        return None
    try:
        return datetime(int(match.group(3)), mes, dia)
    except Exception:
        return None


# ============================================================
# EXTRACCIÓN DE DATOS DE LA SEÑAL
# ============================================================
def extraer_partido(texto):
    patron = re.search(r"🆚\s*(.+?)\s*[-–]\s*(.+?)(?:\n|$)", texto, re.IGNORECASE)
    if patron:
        return patron.group(1).strip(), patron.group(2).strip()
    return "Desconocido", "Desconocido"


def extraer_liga(texto):
    patron = re.search(r"🏆\s*(.+)", texto)
    return patron.group(1).strip() if patron else "Desconocida"


def extraer_fecha(texto):
    patron = re.search(r"🗓\s*(.+)", texto)
    return patron.group(1).strip() if patron else ""


def extraer_cuota(texto):
    patrones = [
        r"🟢\s*\S+\s*:\s*([0-9]+(?:[.,][0-9]+)?)",  # cualquier casa marcada por betmines
        r"bet365\s*:\s*([0-9]+(?:[.,][0-9]+)?)",
        r"pinnacle\s*:\s*([0-9]+(?:[.,][0-9]+)?)",
        r"1xbet\s*:\s*([0-9]+(?:[.,][0-9]+)?)",
        r"cuota\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",
        r"odds?\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)",
    ]
    for patron in patrones:
        resultado = re.search(patron, texto, re.IGNORECASE)
        if resultado:
            try:
                return float(resultado.group(1).replace(",", "."))
            except Exception:
                pass
    return None


def extraer_resultado_deseado(texto):
    patrones = [
        r"🎯\s*Resultado deseado\s*:\s*(.+)",
        r"Resultado deseado\s*:\s*(.+)",
        r"resultado deseado\s*=\s*(.+)",
    ]
    for patron in patrones:
        encontrado = re.search(patron, texto, re.IGNORECASE)
        if encontrado:
            return encontrado.group(1).strip().split("\n")[0].strip()
    return ""


def identificar_mercado(texto):
    t = normalizar(texto)
    resultado_deseado = normalizar(extraer_resultado_deseado(texto))

    if any(x in t for x in ["ambos equipos marcan", "ambos marcan", "btts", "both teams to score"]):
        if " no" in " " + resultado_deseado or resultado_deseado.endswith("no"):
            return "BTTS NO"
        if " si" in " " + resultado_deseado or resultado_deseado.endswith("si"):
            return "BTTS SI"
        if re.search(r"ambos equipos marcan.*no\s+[0-9]", t):
            return "BTTS NO"
        return "BTTS"

    patron = re.search(r"(\+|-)\s*([0-9]+(?:\.[0-9]+)?)", t)
    if patron:
        return f"Más de {patron.group(2)} goles" if patron.group(1) == "+" else f"Menos de {patron.group(2)} goles"

    for patron_str in [r"mas de\s*([0-9]+(?:\.[0-9]+)?)", r"over\s*([0-9]+(?:\.[0-9]+)?)"]:
        m = re.search(patron_str, t)
        if m:
            return f"Más de {m.group(1)} goles"

    for patron_str in [r"menos de\s*([0-9]+(?:\.[0-9]+)?)", r"under\s*([0-9]+(?:\.[0-9]+)?)"]:
        m = re.search(patron_str, t)
        if m:
            return f"Menos de {m.group(1)} goles"

    if "1x2" in t:
        if "empate" in resultado_deseado or resultado_deseado == "x":
            return "1X2 - Empate"
        if "local" in resultado_deseado or resultado_deseado == "1":
            return "1X2 - Local"
        if "visitante" in resultado_deseado or resultado_deseado == "2":
            return "1X2 - Visitante"
        return "1X2"

    if "doble oportunidad" in t or "double chance" in t:
        return f"Doble oportunidad - {resultado_deseado.upper()}" if resultado_deseado else "Doble oportunidad"

    if any(x in t for x in ["empate 1t", "empate al descanso", "empate descanso", "half time draw"]):
        return "Empate 1T"

    if "handicap" in t or "hándicap" in texto.lower():
        return f"Hándicap - {resultado_deseado.upper()}" if resultado_deseado else "Hándicap"

    if "goles equipo local" in t or "team goals home" in t:
        return "Goles equipo local"
    if "goles equipo visitante" in t or "team goals away" in t:
        return "Goles equipo visitante"

    if any(x in t for x in ["corner", "corners", "tiros de esquina"]):
        return f"Corners - {resultado_deseado.upper()}" if resultado_deseado else "Corners"

    if any(x in t for x in ["tarjetas", "cards", "card"]):
        return f"Tarjetas - {resultado_deseado.upper()}" if resultado_deseado else "Tarjetas"

    if "primer equipo en marcar" in t or "first team to score" in t:
        return f"Primer equipo en marcar - {resultado_deseado.upper()}" if resultado_deseado else "Primer equipo en marcar"

    if resultado_deseado:
        return resultado_deseado.upper()

    return "OTRO MERCADO"


def crear_apuesta(texto):
    home, away = extraer_partido(texto)
    return {
        "id": int(time.time() * 1000),
        "fecha_registro": ahora_colombia(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "home": home,
        "away": away,
        "liga": extraer_liga(texto),
        "fecha_partido": extraer_fecha(texto),
        "mercado": identificar_mercado(texto),
        "estrategia": identificar_mercado(texto),
        "resultado_deseado": extraer_resultado_deseado(texto),
        "cuota": extraer_cuota(texto),
        "stake": STAKE,
        "resultado": "pendiente",
        "resultado_manual": False,
        "ganancia": 0,
        "fixture_id": None,
        "goles_home": None,
        "goles_away": None,
        "goles_home_ht": None,
        "goles_away_ht": None,
        "fecha_resultado": None,
        "texto_original": texto,
    }


def apuesta_duplicada(apuestas, nueva):
    for apuesta in apuestas:
        if (
            normalizar(apuesta.get("home", "")) == normalizar(nueva.get("home", ""))
            and normalizar(apuesta.get("away", "")) == normalizar(nueva.get("away", ""))
            and normalizar(apuesta.get("mercado", apuesta.get("estrategia", ""))) == normalizar(nueva.get("mercado", ""))
            and apuesta.get("fecha_partido") == nueva.get("fecha_partido")
        ):
            return True
    return False


# ============================================================
# BOTONES Y MENSAJES DE TELEGRAM
# ============================================================
def botones_apuesta(apuesta):
    return {
        "inline_keyboard": [
            [
                {"text": "✅ GANADA", "callback_data": f"resultado_ganada:{apuesta['id']}"},
                {"text": "❌ PERDIDA", "callback_data": f"resultado_perdida:{apuesta['id']}"},
            ],
            [{"text": "📊 ABRIR PANEL", "callback_data": "panel"}],
        ]
    }


def botones_panel():
    return {
        "inline_keyboard": [
            [{"text": "📊 ACTUALIZAR PANEL", "callback_data": "panel"}],
            [{"text": "🏆 ESTRATEGIAS / MERCADOS", "callback_data": "estrategias"}],
            [{"text": "💹 MERCADO MÁS RENTABLE", "callback_data": "rentabilidad"}],
            [{"text": "🟡 PENDIENTES", "callback_data": "pendientes"}],
        ]
    }


def enviar_apuesta_con_botones(apuesta, chat_id=None):
    if chat_id is None:
        chat_id = CHAT_ID
    cuota = apuesta.get("cuota")
    cuota_texto = f"💵 Cuota: {cuota:.2f}\n" if cuota is not None else ""
    mensaje = (
        "📩 <b>NUEVA APUESTA</b>\n\n"
        f"⚽ {apuesta['home']} - {apuesta['away']}\n\n"
        f"🏆 {apuesta['liga']}\n"
        f"🎯 Mercado: <b>{apuesta['mercado']}</b>\n"
        + (f"🎯 Selección: {apuesta['resultado_deseado']}\n" if apuesta.get("resultado_deseado") else "")
        + cuota_texto
        + f"💰 Apuesta: ${STAKE:,.0f} COP\n"
        "📌 Estado: 🟡 PENDIENTE"
    )
    return telegram_api("sendMessage", {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": "HTML",
        "reply_markup": json.dumps(botones_apuesta(apuesta), ensure_ascii=False),
    })


def registrar_apuesta(texto):
    apuestas = cargar_apuestas()
    nueva = crear_apuesta(texto)

    print("====================================")
    print("📩 NUEVA ALERTA DETECTADA")
    print(f"⚽ {nueva['home']} - {nueva['away']}")
    print(f"🎯 Mercado: {nueva['mercado']}")
    print(f"🎯 Selección: {nueva['resultado_deseado']}")
    print(f"💵 Cuota: {nueva['cuota']}")
    print("====================================")

    if apuesta_duplicada(apuestas, nueva):
        print("ℹ️ Apuesta duplicada")
        return False

    apuestas.append(nueva)
    guardar_apuestas(apuestas)
    print("✅ Apuesta registrada")
    enviar_apuesta_con_botones(nueva)
    return True


# ============================================================
# API-FOOTBALL
# ============================================================
def api_football(endpoint, params=None):
    url = API_URL + endpoint
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    try:
        response = requests.get(url, headers=headers, params=params or {}, timeout=30)
        print(f"⚽ API-Football {response.status_code}")
        if response.status_code != 200:
            print(response.text[:500])
            return None
        data = response.json()
        if data.get("errors"):
            print(f"⚠️ API errors: {data.get('errors')}")
            return None
        return data.get("response", [])
    except Exception as e:
        print(f"❌ Error API-Football: {e}")
        return None


def buscar_fixture(apuesta):
    """Busca el fixture por FECHA REAL del partido (no por 'ahora')."""
    home = apuesta.get("home", "")
    away = apuesta.get("away", "")

    if not home or not away or home == "Desconocido" or away == "Desconocido":
        return None

    fecha_base = parsear_fecha_partido(apuesta.get("fecha_partido", ""))
    if fecha_base is None:
        fecha_base = datetime.now(COLOMBIA_TZ)

    fechas = [(fecha_base + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(-1, 2)]

    for fecha in fechas:
        fixtures = api_football("/fixtures", {"date": fecha, "timezone": "America/Bogota"})
        if not fixtures:
            continue
        for fixture in fixtures:
            equipos = fixture.get("teams", {})
            local = equipos.get("home", {}).get("name", "")
            visitante = equipos.get("away", {}).get("name", "")
            if nombres_equivalentes(home, local) and nombres_equivalentes(away, visitante):
                print(f"✅ PARTIDO ENCONTRADO: {local} vs {visitante}")
                return fixture
    return None


def obtener_fixtures_por_ids(ids):
    """Consulta varios fixture_id ya conocidos en lotes de 20 (ahorra cuota)."""
    resultado = {}
    ids = [i for i in ids if i]
    for i in range(0, len(ids), 20):
        sublote = ids[i:i + 20]
        ids_str = "-".join(str(x) for x in sublote)
        fixtures = api_football("/fixtures", {"ids": ids_str, "timezone": "America/Bogota"})
        if fixtures:
            for fx in fixtures:
                fid = fx.get("fixture", {}).get("id")
                if fid is not None:
                    resultado[fid] = fx
    return resultado


# ============================================================
# DETERMINAR RESULTADO
# ============================================================
def determinar_resultado(apuesta, fixture):
    mercado = normalizar(apuesta.get("mercado", apuesta.get("estrategia", "")))
    deseado = normalizar(apuesta.get("resultado_deseado", ""))
    goals = fixture.get("goals", {})
    score = fixture.get("score", {})
    home_goals = goals.get("home")
    away_goals = goals.get("away")

    if home_goals is None or away_goals is None:
        return None

    total = home_goals + away_goals

    if "btts no" in mercado or ("ambos" in deseado and "no" in deseado):
        return "ganada" if not (home_goals >= 1 and away_goals >= 1) else "perdida"

    if "btts si" in mercado or mercado == "btts" or ("ambos" in deseado and "si" in deseado):
        return "ganada" if (home_goals >= 1 and away_goals >= 1) else "perdida"

    patron = re.search(r"mas de\s*([0-9]+(?:\.[0-9]+)?)", mercado) or re.search(r"over\s*([0-9]+(?:\.[0-9]+)?)", mercado)
    if patron:
        return "ganada" if total > float(patron.group(1)) else "perdida"

    patron = re.search(r"menos de\s*([0-9]+(?:\.[0-9]+)?)", mercado) or re.search(r"under\s*([0-9]+(?:\.[0-9]+)?)", mercado)
    if patron:
        return "ganada" if total < float(patron.group(1)) else "perdida"

    if "empate 1t" in mercado or "empate descanso" in mercado:
        ht = score.get("halftime", {})
        ht_home, ht_away = ht.get("home"), ht.get("away")
        if ht_home is None or ht_away is None:
            return None
        return "ganada" if ht_home == ht_away else "perdida"

    if "1x2" in mercado:
        if "empate" in mercado or deseado == "x":
            return "ganada" if home_goals == away_goals else "perdida"
        if "local" in mercado or deseado == "1":
            return "ganada" if home_goals > away_goals else "perdida"
        if "visitante" in mercado or deseado == "2":
            return "ganada" if away_goals > home_goals else "perdida"

    return None  # mercado no soportado automáticamente -> queda para cierre manual


def calcular_ganancia(apuesta, resultado):
    if resultado == "perdida":
        return -STAKE
    if resultado != "ganada":
        return 0
    try:
        cuota = float(apuesta.get("cuota"))
        if cuota > 1:
            return round(STAKE * (cuota - 1), 2)
    except Exception:
        pass
    return 0


def mensaje_cierre(apuesta, resultado, goles_home=None, goles_away=None):
    icono = "🟢" if resultado == "ganada" else "🔴"
    resultado_texto = "GANADA" if resultado == "ganada" else "PERDIDA"
    cuota = apuesta.get("cuota")
    cuota_texto = f"💵 Cuota: {float(cuota):.2f}\n" if cuota else ""
    marcador = f"📊 Resultado: {goles_home} - {goles_away}\n" if goles_home is not None else ""
    return (
        f"{icono} <b>APUESTA CERRADA</b>\n\n"
        f"⚽ {apuesta['home']} - {apuesta['away']}\n\n"
        f"🏆 {apuesta['liga']}\n"
        f"🎯 Mercado: <b>{apuesta.get('mercado', 'OTRO MERCADO')}</b>\n"
        + (f"🎯 Selección: {apuesta.get('resultado_deseado')}\n" if apuesta.get("resultado_deseado") else "")
        + cuota_texto
        + f"💰 Apuesta: ${STAKE:,.0f} COP\n"
        + marcador
        + f"📌 Estado: <b>{resultado_texto}</b>\n"
        + f"💵 Resultado económico: ${apuesta['ganancia']:,.0f} COP"
    )


def procesar_fixture_encontrado(apuesta, fixture):
    """Evalúa un fixture (nuevo o ya cacheado) y cierra la apuesta si terminó."""
    status = fixture.get("fixture", {}).get("status", {}).get("short")
    if status not in {"FT", "AET", "PEN"}:
        return False

    resultado = determinar_resultado(apuesta, fixture)
    if resultado is None:
        print("⚠️ Mercado no compatible con resultado automático — queda pendiente para cierre manual.")
        return False

    goals = fixture.get("goals", {})
    score = fixture.get("score", {})
    ht = score.get("halftime", {})

    apuesta["resultado"] = resultado
    apuesta["resultado_manual"] = False
    apuesta["ganancia"] = calcular_ganancia(apuesta, resultado)
    apuesta["fixture_id"] = fixture.get("fixture", {}).get("id")
    apuesta["goles_home"] = goals.get("home")
    apuesta["goles_away"] = goals.get("away")
    apuesta["goles_home_ht"] = ht.get("home")
    apuesta["goles_away_ht"] = ht.get("away")
    apuesta["fecha_resultado"] = ahora_colombia()

    enviar(
        mensaje_cierre(apuesta, resultado, goals.get("home"), goals.get("away")),
        CHAT_ID,
        botones_panel(),
    )
    print(f"✅ Cerrada: {resultado}")
    return True


def actualizar_resultados():
    apuestas = cargar_apuestas()
    cambios = False

    pendientes = [a for a in apuestas if a.get("resultado", "pendiente") == "pendiente" and not a.get("resultado_manual", False)]
    print(f"🟡 Pendientes: {len(pendientes)}")

    sin_id = [a for a in pendientes if not a.get("fixture_id")]
    con_id = [a for a in pendientes if a.get("fixture_id")]

    # 1) Los que no tienen fixture_id: buscar por fecha (solo una vez cada uno)
    for apuesta in sin_id:
        print(f"🔎 Buscando: {apuesta.get('home')} vs {apuesta.get('away')}")
        fixture = buscar_fixture(apuesta)
        if not fixture:
            print("⏳ Partido todavía no encontrado")
            continue
        fixture_id = fixture.get("fixture", {}).get("id")
        if fixture_id and apuesta.get("fixture_id") != fixture_id:
            apuesta["fixture_id"] = fixture_id
            cambios = True
        if procesar_fixture_encontrado(apuesta, fixture):
            cambios = True

    # 2) Los que ya tienen fixture_id: consultar TODOS en lote (ahorra cuota)
    ids = [a["fixture_id"] for a in con_id]
    fixtures_por_id = obtener_fixtures_por_ids(ids)
    for apuesta in con_id:
        fixture = fixtures_por_id.get(apuesta.get("fixture_id"))
        if not fixture:
            continue
        if procesar_fixture_encontrado(apuesta, fixture):
            cambios = True

    if cambios:
        guardar_apuestas(apuestas)
        print("💾 signals.json actualizado")
    else:
        print("ℹ️ No hubo resultados nuevos")

    return cambios


# ============================================================
# RESULTADO MANUAL (botones ✅ / ❌)
# ============================================================
def cerrar_apuesta_manual(apuesta, resultado):
    apuesta["resultado"] = resultado
    apuesta["resultado_manual"] = True
    apuesta["ganancia"] = calcular_ganancia(apuesta, resultado)
    apuesta["fecha_resultado"] = ahora_colombia()
    return apuesta


def procesar_resultado_manual(callback, resultado):
    data = callback.get("data", "")
    try:
        apuesta_id = int(data.split(":")[1])
    except Exception:
        telegram_api("answerCallbackQuery", {"callback_query_id": callback.get("id"), "text": "❌ ID inválido", "show_alert": True})
        return

    apuestas = cargar_apuestas()
    encontrada = next((a for a in apuestas if int(a.get("id", -1)) == apuesta_id), None)

    if encontrada is None:
        telegram_api("answerCallbackQuery", {"callback_query_id": callback.get("id"), "text": "❌ Apuesta no encontrada", "show_alert": True})
        return

    if encontrada.get("resultado", "pendiente") != "pendiente":
        telegram_api("answerCallbackQuery", {"callback_query_id": callback.get("id"), "text": "⚠️ Esta apuesta ya está cerrada", "show_alert": True})
        return

    cerrar_apuesta_manual(encontrada, resultado)
    guardar_apuestas(apuestas)

    mensaje = mensaje_cierre(encontrada, resultado)
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    if chat_id and message_id:
        telegram_api("editMessageText", {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": mensaje,
            "parse_mode": "HTML",
            "reply_markup": json.dumps(botones_panel(), ensure_ascii=False),
        })

    texto_resultado = "GANADA" if resultado == "ganada" else "PERDIDA"
    telegram_api("answerCallbackQuery", {"callback_query_id": callback.get("id"), "text": f"Resultado registrado: {texto_resultado}"})
    print(f"✅ Resultado manual: {encontrada['home']} vs {encontrada['away']} = {resultado}")


# ============================================================
# ESTADÍSTICAS
# ============================================================
def calcular_estadisticas(apuestas):
    ganadas = perdidas = pendientes = 0
    ganancia = 0
    for apuesta in apuestas:
        resultado = apuesta.get("resultado", "pendiente")
        if resultado == "ganada":
            ganadas += 1
            ganancia += float(apuesta.get("ganancia", 0))
        elif resultado == "perdida":
            perdidas += 1
            ganancia += float(apuesta.get("ganancia", -STAKE))
        else:
            pendientes += 1

    cerradas = ganadas + perdidas
    efectividad = (ganadas / cerradas * 100) if cerradas else 0
    total_invertido = cerradas * STAKE
    roi = (ganancia / total_invertido * 100) if total_invertido else 0

    return {
        "total": len(apuestas), "ganadas": ganadas, "perdidas": perdidas,
        "pendientes": pendientes, "ganancia": ganancia,
        "efectividad": efectividad, "roi": roi,
    }


def filtrar_por_periodo(apuestas, dias):
    ahora = datetime.now(COLOMBIA_TZ)
    limite = ahora - timedelta(days=dias)
    seleccionadas = []
    for apuesta in apuestas:
        try:
            fecha_dt = datetime.strptime(apuesta.get("fecha_registro"), "%Y-%m-%d %H:%M:%S").replace(tzinfo=COLOMBIA_TZ)
        except Exception:
            continue
        if fecha_dt >= limite:
            seleccionadas.append(apuesta)
    return seleccionadas


def estadisticas_periodo(apuestas, dias):
    return calcular_estadisticas(filtrar_por_periodo(apuestas, dias))


def mercados(apuestas):
    datos = {}
    for apuesta in apuestas:
        nombre = apuesta.get("mercado") or apuesta.get("estrategia") or "OTRO MERCADO"
        if nombre not in datos:
            datos[nombre] = {"total": 0, "ganadas": 0, "perdidas": 0, "pendientes": 0, "ganancia": 0}
        datos[nombre]["total"] += 1
        resultado = apuesta.get("resultado", "pendiente")
        if resultado == "ganada":
            datos[nombre]["ganadas"] += 1
            datos[nombre]["ganancia"] += float(apuesta.get("ganancia", 0))
        elif resultado == "perdida":
            datos[nombre]["perdidas"] += 1
            datos[nombre]["ganancia"] += float(apuesta.get("ganancia", -STAKE))
        else:
            datos[nombre]["pendientes"] += 1

    resultado_lista = []
    for nombre, info in datos.items():
        cerradas = info["ganadas"] + info["perdidas"]
        efectividad = (info["ganadas"] / cerradas * 100) if cerradas else 0
        roi = (info["ganancia"] / (cerradas * STAKE) * 100) if cerradas else 0
        resultado_lista.append((nombre, info, efectividad, roi))

    resultado_lista.sort(key=lambda x: (x[1]["total"], x[1]["ganancia"]), reverse=True)
    return resultado_lista


def mercados_periodo(apuestas, dias):
    return mercados(filtrar_por_periodo(apuestas, dias))


# ============================================================
# PANELES DE TELEGRAM
# ============================================================
def crear_panel():
    apuestas = cargar_apuestas()
    stats = calcular_estadisticas(apuestas)
    dia = estadisticas_periodo(apuestas, 1)
    semana = estadisticas_periodo(apuestas, 7)
    mes = estadisticas_periodo(apuestas, 30)

    return (
        "📊 <b>PANEL FOOTBALL ALERTS</b>\n\n"
        f"💰 <b>Apuesta base:</b> ${STAKE:,.0f} COP\n\n"
        f"🎯 <b>Total:</b> {stats['total']}\n"
        f"🟢 <b>Ganadas:</b> {stats['ganadas']}\n"
        f"🔴 <b>Perdidas:</b> {stats['perdidas']}\n"
        f"🟡 <b>Pendientes:</b> {stats['pendientes']}\n\n"
        f"💵 <b>Ganancia/Pérdida:</b> ${stats['ganancia']:,.0f} COP\n"
        f"📈 <b>Efectividad:</b> {stats['efectividad']:.1f}%\n"
        f"📊 <b>ROI:</b> {stats['roi']:.2f}%\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📅 <b>HOY</b>\n🟢 {dia['ganadas']} | 🔴 {dia['perdidas']} | 🟡 {dia['pendientes']}\n💵 ${dia['ganancia']:,.0f} COP\n\n"
        f"📅 <b>SEMANA</b>\n🟢 {semana['ganadas']} | 🔴 {semana['perdidas']} | 🟡 {semana['pendientes']}\n💵 ${semana['ganancia']:,.0f} COP\n\n"
        f"📅 <b>MES</b>\n🟢 {mes['ganadas']} | 🔴 {mes['perdidas']} | 🟡 {mes['pendientes']}\n💵 ${mes['ganancia']:,.0f} COP"
    )


def crear_panel_mercados():
    datos = mercados(cargar_apuestas())
    if not datos:
        return "🏆 <b>ESTRATEGIAS / MERCADOS</b>\n\nTodavía no hay apuestas registradas."

    mensaje = "🏆 <b>ESTRATEGIAS / MERCADOS (TOTAL)</b>\n\n"
    for i, (nombre, info, efectividad, roi) in enumerate(datos, 1):
        mensaje += (
            f"{i}. <b>{nombre}</b>\n"
            f"   🎯 {info['total']} | 🟢 {info['ganadas']} | 🔴 {info['perdidas']} | 🟡 {info['pendientes']}\n"
            f"   📈 {efectividad:.1f}% | 📊 ROI {roi:.2f}%\n"
            f"   💵 ${info['ganancia']:,.0f} COP\n\n"
        )
    return mensaje


def crear_resumen_rentabilidad():
    """Muestra el mercado MÁS RENTABLE de hoy, la semana y el mes."""
    apuestas = cargar_apuestas()
    mensaje = "💹 <b>MERCADO MÁS RENTABLE</b>\n\n"

    for titulo, dias in [("HOY", 1), ("SEMANA", 7), ("MES", 30)]:
        datos = mercados_periodo(apuestas, dias)
        cerrados = [d for d in datos if (d[1]["ganadas"] + d[1]["perdidas"]) > 0]
        mensaje += f"📅 <b>{titulo}</b>\n"
        if not cerrados:
            mensaje += "   Sin apuestas cerradas todavía.\n\n"
            continue
        nombre, info, efectividad, roi = max(cerrados, key=lambda x: x[1]["ganancia"])
        mensaje += (
            f"   🏆 {nombre}\n"
            f"   🎯 {info['total']} | 🟢 {info['ganadas']} | 🔴 {info['perdidas']}\n"
            f"   📈 {efectividad:.1f}% | 📊 ROI {roi:.2f}%\n"
            f"   💵 ${info['ganancia']:,.0f} COP\n\n"
        )
    return mensaje


def crear_pendientes():
    pendientes = [a for a in cargar_apuestas() if a.get("resultado", "pendiente") == "pendiente"]
    if not pendientes:
        return "🟡 <b>PENDIENTES</b>\n\nNo hay apuestas pendientes."

    mensaje = "🟡 <b>APUESTAS PENDIENTES</b>\n\n"
    for apuesta in pendientes[-20:]:
        cuota = apuesta.get("cuota")
        cuota_texto = f"💵 Cuota: {float(cuota):.2f}\n" if cuota else ""
        mensaje += (
            f"🆔 {apuesta['id']}\n"
            f"⚽ {apuesta['home']} - {apuesta['away']}\n"
            f"🎯 {apuesta.get('mercado', 'OTRO MERCADO')}\n"
            + cuota_texto
            + f"💰 ${STAKE:,.0f} COP\n\n"
        )
    return mensaje


def enviar_panel(chat_id):
    enviar(crear_panel(), chat_id, botones_panel())


# ============================================================
# CALLBACKS Y COMANDOS
# ============================================================
def responder_callback(callback):
    data = callback.get("data", "")

    if data.startswith("resultado_ganada:"):
        procesar_resultado_manual(callback, "ganada")
        return
    if data.startswith("resultado_perdida:"):
        procesar_resultado_manual(callback, "perdida")
        return

    telegram_api("answerCallbackQuery", {"callback_query_id": callback.get("id")})

    chat_id = callback.get("message", {}).get("chat", {}).get("id")
    if not chat_id:
        return

    if data == "panel":
        enviar_panel(chat_id)
    elif data == "estrategias":
        enviar(crear_panel_mercados(), chat_id, botones_panel())
    elif data == "rentabilidad":
        enviar(crear_resumen_rentabilidad(), chat_id, botones_panel())
    elif data == "pendientes":
        enviar(crear_pendientes(), chat_id, botones_panel())


def procesar_comando(chat_id, texto):
    comando = texto.split()[0].lower().split("@")[0]

    if comando == "/start":
        enviar(
            "⚽ <b>FOOTBALL ALERTS</b>\n\n✅ Bot conectado correctamente.\n\n"
            "📊 /panel\n🏆 /mercados\n💹 /rentabilidad\n🟡 /pendientes",
            chat_id, botones_panel(),
        )
    elif comando == "/panel":
        enviar_panel(chat_id)
    elif comando in ("/mercados", "/estrategias"):
        enviar(crear_panel_mercados(), chat_id, botones_panel())
    elif comando == "/rentabilidad":
        enviar(crear_resumen_rentabilidad(), chat_id, botones_panel())
    elif comando == "/pendientes":
        enviar(crear_pendientes(), chat_id, botones_panel())


def procesar_mensaje(message):
    chat_id = message.get("chat", {}).get("id")
    texto = message.get("text", "")

    if not texto or str(chat_id) != str(CHAT_ID):
        return

    if texto.startswith("/"):
        procesar_comando(chat_id, texto)
        return

    if any(x in texto for x in ["NUEVA APUESTA", "APUESTA CERRADA", "PANEL FOOTBALL ALERTS", "ESTRATEGIAS / MERCADOS", "MERCADO MÁS RENTABLE"]):
        return

    registrar_apuesta(texto)


def recibir_telegram():
    estado = cargar_estado()
    offset = estado.get("last_update_id", 0)
    if offset:
        offset += 1

    inicio = time.time()
    print("📡 Escuchando Telegram...")

    while time.time() - inicio < POLL_SECONDS:
        parametros = {"timeout": 5}
        if offset:
            parametros["offset"] = offset

        respuesta = telegram_api("getUpdates", parametros)
        if not respuesta:
            time.sleep(2)
            continue

        for update in respuesta.get("result", []):
            update_id = update.get("update_id")
            if update_id is not None:
                offset = update_id + 1
                estado["last_update_id"] = update_id
                guardar_estado(estado)

            if "callback_query" in update:
                responder_callback(update["callback_query"])
            elif "message" in update:
                procesar_mensaje(update["message"])

        time.sleep(1)

    print("📡 Fin de recepción Telegram")


# ============================================================
# EJECUCIÓN — soporta GitHub Actions (una pasada) y VPS (loop)
# ============================================================
def ejecutar_ciclo():
    """Una pasada completa: recibir Telegram + actualizar resultados."""
    recibir_telegram()
    print("⚽ ACTUALIZANDO RESULTADOS...")
    actualizar_resultados()

    apuestas = cargar_apuestas()
    stats = calcular_estadisticas(apuestas)
    print("====================================")
    print(f"📊 Total: {stats['total']} | 🟢 {stats['ganadas']} | 🔴 {stats['perdidas']} | 🟡 {stats['pendientes']}")
    print(f"💵 ${stats['ganancia']:,.0f} COP | 📈 {stats['efectividad']:.1f}% | ROI {stats['roi']:.2f}%")
    print("====================================")


def main():
    en_github_actions = os.getenv("GITHUB_ACTIONS") == "true"

    if en_github_actions:
        print("🚀 EJECUCIÓN ÚNICA (GitHub Actions)")
        ejecutar_ciclo()
        print("✅ EJECUCIÓN TERMINADA")
    else:
        print("🚀 BOT INICIADO (loop continuo — VPS)")
        estado = cargar_estado()
        ultima_verificacion = estado.get("ultima_verificacion_resultados", 0)

        while True:
            recibir_telegram()
            ahora_ts = time.time()
            if ahora_ts - ultima_verificacion >= RESULTADOS_INTERVALO:
                print("⚽ ACTUALIZANDO RESULTADOS...")
                actualizar_resultados()
                ultima_verificacion = ahora_ts
                estado = cargar_estado()
                estado["ultima_verificacion_resultados"] = ultima_verificacion
                guardar_estado(estado)

                apuestas = cargar_apuestas()
                stats = calcular_estadisticas(apuestas)
                print("====================================")
                print(f"📊 Total: {stats['total']} | 🟢 {stats['ganadas']} | 🔴 {stats['perdidas']} | 🟡 {stats['pendientes']}")
                print(f"💵 ${stats['ganancia']:,.0f} COP | 📈 {stats['efectividad']:.1f}% | ROI {stats['roi']:.2f}%")
                print("====================================")


if __name__ == "__main__":
    main()
