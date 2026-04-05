# 🤖 Telegram Mute Bot

بوت تيليجرام لكتم الأشخاص المزعجين — يحذف رسائلهم تلقائياً في الخاص والمجموعات.

> ⚠️ **يحذف فقط رسائل الأشخاص اللي تكتمهم أنت يدوياً** — لا يكتم أي شخص تلقائياً.

## ✨ المميزات

- **كتم يدوي في الخاص**: أضف أي شخص لقائمة الكتم عبر لوحة التحكم (باليوزرنيم أو الآيدي)
- **كتم في المجموعات**: رد على رسالة شخص واكتب `/mute` لكتمه
- **حذف تلقائي**: رسائل المكتومين تُحذف فوراً عند وصولها
- **لوحة تحكم**: بوت تيليجرام منفصل لإدارة قوائم الكتم والاستثناءات
- **إشعارات**: يرسل لك إشعار عند كتم أو إلغاء كتم شخص
- **إعداد سهل**: يطلب البيانات مرة واحدة فقط ويحفظها

## 🏗️ بنية المشروع

| الملف | الوظيفة |
|-------|---------|
| `main.py` | المشغّل الرئيسي — يربط كل شيء |
| `userbot.py` | اليوزر بوت (Telethon MTProto) — يراقب ويحذف رسائل المكتومين |
| `bot.py` | بوت التحكم (python-telegram-bot) — لوحة الإدارة |
| `data_manager.py` | إدارة البيانات وقوائم الكتم |
| `config.py` | تحميل الإعدادات من `credentials.json` |

## 📋 المتطلبات

- Python 3.9+
- حساب Telegram شخصي
- بوت من [@BotFather](https://t.me/BotFather)
- API_ID و API_HASH من [my.telegram.org](https://my.telegram.org)

## 📦 التثبيت

### Windows

```powershell
# 1. استنساخ المشروع
git clone https://github.com/karrartyhg162-art/botmute.git
cd botmute

# 2. تثبيت المكتبات
pip install -r requirements.txt

# 3. تشغيل البوت (سيطلب البيانات تلقائياً في أول مرة)
python main.py
```

### Termux (Android)

```bash
# 1. تثبيت الحزم
pkg update && pkg upgrade -y
pkg install python git -y

# 2. استنساخ المشروع
git clone https://github.com/karrartyhg162-art/botmute.git
cd botmute

# 3. تثبيت المكتبات
pip install -r requirements.txt

# 4. تشغيل البوت
python main.py
```

### Linux

```bash
git clone https://github.com/karrartyhg162-art/botmute.git
cd botmute
pip install -r requirements.txt
python main.py
```

## ⚙️ الإعداد (مرة واحدة فقط)

عند أول تشغيل، سيطلب منك البيانات التالية ويحفظها تلقائياً:

| البيان | الوصف | من أين تحصل عليه |
|--------|-------|-----------------|
| `API_ID` | معرّف التطبيق (رقم) | [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | مفتاح التطبيق (نص) | [my.telegram.org](https://my.telegram.org) |
| `PHONE_NUMBER` | رقم هاتفك مع كود الدولة | مثال: `+966512345678` |
| `BOT_TOKEN` | توكن البوت | [@BotFather](https://t.me/BotFather) |
| `OWNER_ID` | آيدي حسابك | [@userinfobot](https://t.me/userinfobot) |

> 💡 البيانات تُحفظ في `credentials.json` محلياً ولا تُرفع على GitHub.

## 📱 أوامر البوت

| الأمر | الوظيفة |
|-------|---------|
| `/start` | بدء البوت وعرض لوحة التحكم |
| `/mute` | كتم شخص في المجموعة (رد على رسالته) |
| `/unmute` | إلغاء كتم شخص في المجموعة (رد على رسالته) |

## 🔄 التشغيل في الخلفية (Termux)

```bash
# تشغيل في الخلفية
nohup python main.py > output.log 2>&1 &

# مراقبة السجلات
tail -f output.log

# إيقاف البوت
pkill -f "python main.py"
```

## ⚠️ ملاحظات مهمة

- عند أول تشغيل سيطلب **كود التحقق** — ابحث عنه في تطبيق Telegram (رسالة من "Telegram")
- **لا تحذف** ملفات `.session` — تحتوي على جلسة تسجيل الدخول
- **لا تشارك** `credentials.json` — يحتوي على بياناتك الحساسة
- البوت يحذف **فقط** رسائل الأشخاص المكتومين يدوياً

## 📄 الرخصة

MIT License
