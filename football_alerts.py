"""
Bot de Telegram - Panel de Apuestas Betmines
---------------------------------------------
Flujo:
1. Pegas manualmente el texto de la alerta de Betmines en el chat del bot.
2. El bot la parsea, calcula el monto (stake fijo) y la REGISTRA de una vez
   en la base de datos con estado "pendiente" (queda guardada aunque no
   hayas confirmado nada todavía).
3. Te responde con botones para confirmar la apuesta o ignorarla.
4. Al confirmar, pasa a "en_juego" y un job en segundo plano revisa el
   resultado automáticamente contra una API deportiva (ejemplo API-FOOTBALL,
   ajustable a la que uses) y la marca GANADA / PERDIDA sola.
5. Panel principal con menú persistente (Rendimiento, Estrategias,
   Calendario, Pendientes, Ganancias, Estadísticas, Configuración), similar
   al de la captura que compartiste.

REQUISITOS:
    pip install python-telegram-bot==21.4 requests

CONFIGURA ABAJO:
    - BOT_TOKEN      -> token de tu bot (@BotFather)
    - NOTIFY_CHAT_ID -> tu chat con el bot (donde pegas alertas y ves el panel)
    - STAKE_BASE     -> monto fijo que apuestas por alerta (ej 5000 COP)
    - SPORTS_API_KEY -> tu key de API-FOOTBALL (o la API que uses)

NOTA: `resolver_resultado()` cubre 1X2 de fútbol como ejemplo. Si manejas
otros mercados (over/under, hándicap, etc.) o deportes, hay que adaptar esa
función y `buscar_fixture()` a la API que uses.
"""

import re
import sqlite3
from datetime import datetime

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, ContextTypes, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)

# ----------------- CONFIG -----------------
BOT_TOKEN = "TU_TOKEN_AQUI"
NOTIFY_CHAT_ID = 123456789           # tu chat con el bot
STAKE_BASE = 5000                    # monto fijo por apuesta (COP)
SPORTS_API_KEY = "TU_API_KEY_AQUI"
SPORTS_API_HOST = "v3.football.api-sports.io"
CHECK_INTERVAL_SECONDS = 600         # cada cuánto revisa resultados pendientes
# -------------------------------------------

DB_PATH = "apuestas.db"

MENU = {
    "rendimiento": "📊 Rendimiento",
    "estrategias": "🎯 Estrategias",
    "calendario": "📅 Calendario",
    "pendientes": "⏳ Pendientes",
    "ganancias": "💰 Ganancias",
    "estadisticas": "📈 Estadísticas",
    "configuracion": "⚙️ Configuración",
}


def teclado_principal():
    return ReplyKeyboardMarkup(
        [
            [MENU["rendimiento"], MENU["estrategias"]],
            [MENU["calendario"], MENU["pendientes"]],
            [MENU["ganancias"], MENU["estadisticas"]],
            [MENU["configuracion"]],
        ],
        resize_keyboard=True
    )


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS apuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipo_local TEXT,
            equipo_visita TEXT,
            pick TEXT,
            cuota REAL,
            monto REAL,
            estado TEXT DEFAULT 'pendiente',
            fixture_id INTEGER,
            creado TEXT
        )
    """)
    con.commit()
    con.close()


def parsear_alerta(texto: str):
    """Ajusta este regex al formato real de las alertas de Betmines."""
    m = re.search(
        r"([A-Za-zÀ-ÿ ]+)\s*(?:vs|-)\s*([A-Za-zÀ-ÿ ]+).*?(?:pick|apuesta)[:\s]*([A-Za-z0-9 ]+).*?cuota[:\s]*([\d.]+)",
        texto, re.IGNORECASE | re.DOTALL
    )
    if not m:
        return None
    local, visita, pick, cuota = m.groups()
    return {
        "local": local.strip(),
        "visita": visita.strip(),
        "pick": pick.strip(),
        "cuota": float(cuota),
    }


# ---------------- Registro y stats ----------------

def registrar_apuesta(datos: dict) -> int:
    """Guarda la apuesta apenas se pega la alerta, con estado 'pendiente'."""
    con = sqlite3.connect(DB_PATH)
    cur = con.execute(
        "INSERT INTO apuestas (equipo_local, equipo_visita, pick, cuota, monto, estado, creado) "
        "VALUES (?,?,?,?,?, 'pendiente', ?)",
        (datos["local"], datos["visita"], datos["pick"], datos["cuota"], STAKE_BASE, datetime.now().isoformat())
    )
    con.commit()
    apuesta_id = cur.lastrowid
    con.close()
    return apuesta_id


def obtener_stats():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    resueltas = con.execute("SELECT * FROM apuestas WHERE estado IN ('ganada','perdida')").fetchall()
    con.close()

    ganadas = [f for f in resueltas if f["estado"] == "ganada"]
    perdidas = [f for f in resueltas if f["estado"] == "perdida"]

    resultado = sum(
        f["monto"] * (f["cuota"] - 1) if f["estado"] == "ganada" else -f["monto"]
        for f in resueltas
    )
    total = len(resueltas)
    efectividad = (len(ganadas) / total * 100) if total else 0.0
    invertido = STAKE_BASE * total
    roi = (resultado / invertido * 100) if invertido else 0.0

    return {
        "ganadas": len(ganadas),
        "perdidas": len(perdidas),
        "efectividad": efectividad,
        "roi": roi,
        "resultado": resultado,
    }


def clasificar_pick(pick: str) -> str:
    """Agrupa el pick en una 'estrategia'/mercado. Ajusta las palabras clave
    si tus alertas de Betmines usan otra terminología."""
    p = pick.lower()
    if "empate" in p or "draw" in p:
        return "Empate"
    if "más de" in p or "mas de" in p or "over" in p:
        return "Más de (Over)"
    if "menos de" in p or "under" in p:
        return "Menos de (Under)"
    if "hándicap" in p or "handicap" in p:
        return "Hándicap"
    if "ambos" in p or "btts" in p:
        return "Ambos anotan"
    if "local" in p:
        return "Gana Local"
    if "visita" in p:
        return "Gana Visitante"
    return "Otro"


def obtener_stats_por_estrategia():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    resueltas = con.execute("SELECT * FROM apuestas WHERE estado IN ('ganada','perdida')").fetchall()
    con.close()

    grupos = {}
    for f in resueltas:
        cat = clasificar_pick(f["pick"])
        g = grupos.setdefault(cat, {"ganadas": 0, "perdidas": 0, "resultado": 0.0, "total": 0})
        g["total"] += 1
        if f["estado"] == "ganada":
            g["ganadas"] += 1
            g["resultado"] += f["monto"] * (f["cuota"] - 1)
        else:
            g["perdidas"] += 1
            g["resultado"] -= f["monto"]

    lista = []
    for cat, g in grupos.items():
        invertido = STAKE_BASE * g["total"]
        roi = (g["resultado"] / invertido * 100) if invertido else 0.0
        efectividad = (g["ganadas"] / g["total"] * 100) if g["total"] else 0.0
        lista.append({"categoria": cat, "roi": roi, "efectividad": efectividad, **g})

    lista.sort(key=lambda x: x["resultado"], reverse=True)
    return lista


def panel_texto() -> str:
    s = obtener_stats()
    return (
        f"✅ Ganadas\n{s['ganadas']}\n\n"
        f"❌ Perdidas\n{s['perdidas']}\n"
        f"{'-'*30}\n"
        f"🎯 Ef
