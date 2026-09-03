import os
import asyncio
from telethon import TelegramClient, events

from football_alerts import registrar_apuesta

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

BETMINES_CHAT_NAMES = {
    nombre.strip().lower()
    for nombre in os.getenv(
        "BETMINES_CHAT_NAME",
        "BetMines Pre Match Scanner"
    ).split(",")
    if nombre.strip()
}

if not API_ID or not API_HASH or not PHONE:
    print("❌ Faltan TELEGRAM_API_ID, TELEGRAM_API_HASH o TELEGRAM_PHONE")
    raise SystemExit(1)

SESSION_NAME = "betmines_session"

client = TelegramClient(
    SESSION_NAME,
    int(API_ID),
    API_HASH
)

def normalizar_nombre(nombre):
    return " ".join((nombre or "").strip().lower().split())

@client.on(events.NewMessage)
async def manejar_mensaje_nuevo(event):
    chat = await event.get_chat()

    nombre_chat = (
        getattr(chat, "title", None)
        or getattr(chat, "first_name", "")
        or ""
    )

    nombre_normalizado = normalizar_nombre(nombre_chat)

    if nombre_normalizado not in BETMINES_CHAT_NAMES:
        return

    texto = event.raw_text

    if not texto or len(texto.strip()) < 10:
        return

    print("====================================")
    print("📩 Alerta recibida de BetMines")
    print(f"💬 Chat: {nombre_chat}")
    print("====================================")

    try:
        registrar_apuesta(texto)
        print("✅ Apuesta registrada correctamente")
    except Exception as e:
        print(f"❌ Error registrando apuesta desde BetMines: {e}")

async def main():
    await client.start(phone=PHONE)

    print("====================================")
    print("⚽ FOOTBALL ALERTS")
    print("====================================")
    print("✅ Sesión de Telegram iniciada correctamente")
    print("📡 Escuchando chats:")

    for chat_name in BETMINES_CHAT_NAMES:
        print(f"   • {chat_name}")

    print("====================================")

    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
