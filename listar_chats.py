"""
listar_chats.py

Utilidad de UNA SOLA VEZ para ver el nombre EXACTO de tus chats de Telegram
(incluyendo el de BetMines), usando las mismas credenciales de Telethon.

Uso:
    python3 listar_chats.py

Te va a pedir el código de verificación la primera vez (igual que
listener_betmines.py). Después imprime la lista de tus últimos chats
con su nombre completo, para que copies el exacto y lo pongas en
la variable de entorno BETMINES_CHAT_NAME.
"""

import os
import asyncio
from telethon import TelegramClient

API_ID = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")

if not API_ID or not API_HASH or not PHONE:
    print("❌ Faltan TELEGRAM_API_ID, TELEGRAM_API_HASH o TELEGRAM_PHONE")
    raise SystemExit(1)

client = TelegramClient("betmines_session", int(API_ID), API_HASH)


async def main():
    await client.start(phone=PHONE)
    print("====================================")
    print("📋 TUS CHATS (nombre exacto)")
    print("====================================")

    async for dialog in client.iter_dialogs(limit=30):
        print(f"- '{dialog.name}'")

    print("====================================")
    print("👉 Copia el nombre EXACTO del chat de BetMines")
    print("   (tal cual aparece entre comillas arriba)")
    print("====================================")


if __name__ == "__main__":
    asyncio.run(main())
