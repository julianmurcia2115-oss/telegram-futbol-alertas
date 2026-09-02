"""
listener_betmines.py

Escucha automáticamente el chat de Telegram con el bot de BetMines
(usando TU cuenta personal, vía Telethon) y registra cada alerta nueva
directamente en signals.json, usando las mismas funciones de
football_alerts.py — sin necesidad de copiar y pegar nada.

Requiere variables de entorno:
    TELEGRAM_API_ID       -> tu api_id de my.telegram.org
    TELEGRAM_API_HASH     -> tu api_hash de my.telegram.org
    TELEGRAM_PHONE        -> tu número con indicativo, ej: +573001234567
    BETMINES_CHAT_NAME    -> nombre exacto del chat, ej: "BetMines Pre Match Scanner"

La PRIMERA vez que corra, Telegram te va a pedir un código de verificación
(te llega a tu app de Telegram). Lo escribes cuando el script lo pida.
Después de esa primera vez, la sesión queda guardada en el archivo
"betmines_session.session" y no vuelve a pedir el código.

IMPORTANTE: el archivo .session da acceso a tu cuenta de Telegram.
Nunca lo subas a GitHub — agrégalo a tu .gitignore.
"""

import os
import asyncio
from telethon import TelegramClient, events

# Reutilizamos la lógica que ya existe en football_alerts.py
from football_alerts import registrar_apuesta

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")
BETMINES_CHAT_NAME = os.getenv("BETMINES_CHAT_NAME", "BetMines Pre Match Scanner")

if not API_ID or not API_HASH or not PHONE:
    print("❌ Faltan TELEGRAM_API_ID, TELEGRAM_API_HASH o TELEGRAM_PHONE")
    raise SystemExit(1)

SESSION_NAME = "betmines_session"

client = TelegramClient(SESSION_NAME, int(API_ID), API_HASH)


@client.on(events.NewMessage)
async def manejar_mensaje_nuevo(event):
    """Se dispara con CADA mensaje nuevo que tu cuenta recibe.
    Filtramos para quedarnos solo con los del chat de BetMines."""

    chat = await event.get_chat()
    nombre_chat = getattr(chat, "title", None) or getattr(chat, "first_name", "")

    if BETMINES_CHAT_NAME.lower() not in (nombre_chat or "").lower():
        return  # no es el chat de BetMines, ignorar

    texto = event.raw_text

    if not texto or len(texto.strip()) < 10:
        return

    print("====================================")
    print(f"📩 Alerta recibida de BetMines ({nombre_chat})")
    print("====================================")

    try:
        registrar_apuesta(texto)
    except Exception as e:
        print(f"❌ Error registrando apuesta desde BetMines: {e}")


async def main():
    await client.start(phone=PHONE)
    print("✅ Sesión de Telegram iniciada correctamente")
    print(f"📡 Escuchando el chat: {BETMINES_CHAT_NAME}")
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
