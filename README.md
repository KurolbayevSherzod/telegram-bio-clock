# Telegram Bio Clock

Telegram bio'ingizga Toshkent vaqti bilan doimiy yangilanadigan soat qo'yadi.

## 1. O'rnatish

```powershell
cd "$env:USERPROFILE\Desktop\TelegramBioClock"
python -m pip install -r requirements.txt
```

## 2. Sozlash

`.env.example` faylidan nusxa olib `.env` yarating:

```powershell
Copy-Item .env.example .env
notepad .env
```

`TELEGRAM_API_ID` va `TELEGRAM_API_HASH` qiymatlarini https://my.telegram.org/apps sahifasidan oling.

## 3. Ishga tushirish

```powershell
python bio_clock.py
```

Birinchi marta ishga tushganda Telegram telefon raqamingizni, keyin kodni so'raydi.

## Eslatma

Telegram bio'ni juda tez yangilashga limit qo'yadi. Skript barqaror ishlashi uchun bio'ni 60 sekundda bir marta yangilaydi.
