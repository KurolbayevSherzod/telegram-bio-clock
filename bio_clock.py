import asyncio
import logging
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from zoneinfo import ZoneInfo

from dotenv import load_dotenv, set_key
from telethon import TelegramClient, functions
from telethon.errors import FloodWaitError, RPCError
from telethon.sessions import StringSession


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
SESSION_FILE = os.path.join(BASE_DIR, "telegram_bio_clock")
LOG_FILE = os.path.join(BASE_DIR, "bio_clock.log")

BIO_CHAR_LIMIT = 70

WEEKDAYS_UZ = [
    "Dushanba", "Seshanba", "Chorshanba", "Payshanba",
    "Juma", "Shanba", "Yakshanba"
]
WEEKDAYS_SHORT_UZ = ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Yak"]
MONTHS_UZ = [
    "Yanvar", "Fevral", "Mart", "Aprel", "May", "Iyun",
    "Iyul", "Avgust", "Sentyabr", "Oktyabr", "Noyabr", "Dekabr"
]
EMOJI_DIGITS = {
    "0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣",
    "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣", ":": ":"
}

handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=handlers,
)
logger = logging.getLogger("BioClock")


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value.strip())
    except ValueError:
        return default


def stylize_emoji_time(time_str: str) -> str:
    return "".join(EMOJI_DIGITS.get(ch, ch) for ch in time_str)


def make_bio(template: str, timezone_name: str) -> str:
    now = datetime.now(ZoneInfo(timezone_name))
    time_str = now.strftime("%H:%M")
    emoji_time = stylize_emoji_time(time_str)
    weekday_uz = WEEKDAYS_UZ[now.weekday()]
    weekday_short = WEEKDAYS_SHORT_UZ[now.weekday()]
    month_uz = MONTHS_UZ[now.month - 1]
    date_uz = f"{now.day}-{month_uz}"

    bio = template.format(
        time=time_str,
        emoji_time=emoji_time,
        date=now.strftime("%d.%m.%Y"),
        date_uz=date_uz,
        weekday_uz=weekday_uz,
        weekday_short=weekday_short,
        tz=timezone_name,
    )
    return bio[:BIO_CHAR_LIMIT]


def start_health_server_if_needed() -> None:
    """Render / Koyeb kabi bepul bulutli serverlar uchun mini HTTP health-check server."""
    port = env_int("PORT", 0)
    if port <= 0:
        return

    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Telegram Bio Clock is running OK")

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health-check HTTP server {port}-portda ishga tushdi.")


async def main() -> None:
    load_dotenv(ENV_FILE)

    api_id = env_int("TELEGRAM_API_ID", 0)
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    phone = os.getenv("TELEGRAM_PHONE", "").strip()
    session_string = os.getenv("TELEGRAM_SESSION_STRING", "").strip()
    timezone_name = os.getenv("TIMEZONE", "Asia/Tashkent").strip()
    template = os.getenv(
        "BIO_TEMPLATE",
        "⏰ Hozirgi vaqt: {time} | 🗓 {date_uz}, {weekday_short} | Teacher 👨‍🏫"
    ).strip()
    run_duration = env_int("RUN_DURATION_SECONDS", 0)

    if not api_id or not api_hash or api_id == 123456:
        raise SystemExit(
            "Xatolik: .env faylda TELEGRAM_API_ID va TELEGRAM_API_HASH ko'rsatilmagan!"
        )

    start_health_server_if_needed()

    session = StringSession(session_string) if session_string else SESSION_FILE
    client = TelegramClient(session, api_id, api_hash)

    await client.start(phone=phone if phone else lambda: input("Telefon raqamingiz (+998...): "))
    me = await client.get_me()
    logger.info(f"Muvaffaqiyatli ulandi: {me.first_name} (ID: {me.id})")

    # Agar StringSession hali .env ga saqlanmagan bo'lsa, avtomatik saqlab qo'yamiz
    if not session_string and os.path.exists(ENV_FILE):
        try:
            exported = StringSession.save(client.session)
            if exported:
                set_key(ENV_FILE, "TELEGRAM_SESSION_STRING", exported)
                logger.info("Bulutli server uchun TELEGRAM_SESSION_STRING .env faylga saqlandi.")
        except Exception as exc:
            logger.warning(f"StringSession saqlashda xatolik: {exc}")

    last_bio = None
    start_ts = asyncio.get_event_loop().time()

    try:
        while True:
            if run_duration > 0 and (asyncio.get_event_loop().time() - start_ts) >= run_duration:
                logger.info("Belgilangan RUN_DURATION_SECONDS vaqti tugadi. Dastur yakunlanmoqda.")
                break

            try:
                load_dotenv(ENV_FILE, override=True)
                template = os.getenv(
                    "BIO_TEMPLATE",
                    "⏰ Hozirgi vaqt: {time} | 🗓 {date_uz}, {weekday_short} | Teacher 👨‍🏫"
                ).strip()
                bio = make_bio(template, timezone_name)
                if bio != last_bio:
                    await client(functions.account.UpdateProfileRequest(about=bio))
                    last_bio = bio
                    logger.info(f"Bio yangilandi: {bio}")
            except FloodWaitError as exc:
                wait_seconds = int(exc.seconds) + 5
                logger.warning(f"Telegram FloodWait cheklovi: {wait_seconds} soniya kutilmoqda...")
                await asyncio.sleep(wait_seconds)
                continue
            except RPCError as exc:
                logger.error(f"Telegram RPC xatoligi: {exc}")
                await asyncio.sleep(15)
                continue
            except Exception as exc:
                logger.error(f"Kutilmagan xatolik (internet yoki aloqa): {exc}")
                await asyncio.sleep(15)
                continue

            # Keyingi daqiqaning aniq 00-soniyasigacha kutish
            now = datetime.now(ZoneInfo(timezone_name))
            sleep_seconds = max(60 - now.second - (now.microsecond / 1_000_000) + 0.2, 5.0)
            await asyncio.sleep(sleep_seconds)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Foydalanuvchi tomonidan to'xtatildi.")
