# 🤖 Telegram Auto-Mute Bot

بوت كتم تلقائي لتيليجرام — يحذف رسائل الأشخاص المكتومين في الخاص تلقائياً.

## ✨ المميزات

- **كتم تلقائي في الخاص**: أي شخص غريب يراسلك يُكتم تلقائياً وتُحذف رسائله
- **كتم يدوي في الخاص**: أضف أي شخص لقائمة الكتم من لوحة التحكم
- **كتم في المجموعات**: رد على رسالة شخص واكتب `/mute` لكتمه
- **لوحة تحكم**: بوت تيليجرام منفصل لإدارة قوائم الكتم
- **قائمة بيضاء**: استثناء أشخاص من الكتم التلقائي

## 🏗️ البنية

| الملف | الوظيفة |
|-------|---------|
| `main.py` | المشغّل الرئيسي |
| `userbot.py` | اليوزر بوت (Telethon) — يراقب ويحذف الرسائل |
| `bot.py` | بوت التحكم (python-telegram-bot) — لوحة الإدارة |
| `data_manager.py` | إدارة البيانات (data.json) |
| `config.py` | الإعدادات (لا يُرفع على GitHub) |

## 📦 التثبيت على Termux (Android)

```bash
# 1. تثبيت الحزم الأساسية
pkg update && pkg upgrade -y
pkg install python git -y

# 2. استنساخ المشروع
git clone https://github.com/frfshtete/botmute.git
cd botmute

# 3. تثبيت المكتبات
pip install -r requirements.txt

# 4. إنشاء ملف الإعدادات
cp config.example.py config.py

# 5. تعديل الإعدادات (أدخل بياناتك)
nano config.py

# 6. تشغيل البوت
python main.py
```

## 🖥️ التشغيل على Windows

```powershell
# 1. استنساخ المشروع
git clone https://github.com/frfshtete/botmute.git
cd botmute

# 2. تثبيت المكتبات
pip install -r requirements.txt

# 3. إنشاء ملف الإعدادات
copy config.example.py config.py

# 4. تعديل الإعدادات
notepad config.py

# 5. تشغيل البوت
python main.py
```

## ⚙️ الإعدادات المطلوبة (config.py)

| المتغير | الوصف | من أين تحصل عليه |
|---------|-------|-----------------|
| `API_ID` | معرّف التطبيق | [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | مفتاح التطبيق | [my.telegram.org](https://my.telegram.org) |
| `PHONE_NUMBER` | رقم هاتفك | مثال: `"+966512345678"` |
| `BOT_TOKEN` | توكن البوت | [@BotFather](https://t.me/BotFather) |
| `OWNER_ID` | آيدي حسابك | [@userinfobot](https://t.me/userinfobot) |

## 📱 التشغيل في الخلفية على Termux

```bash
# تشغيل في الخلفية (لا يتوقف عند إغلاق Termux)
nohup python main.py > output.log 2>&1 &

# لمراقبة اللوج
tail -f output.log

# لإيقاف البوت
pkill -f "python main.py"
```

## ⚠️ ملاحظات مهمة

- عند أول تشغيل سيطلب كود التحقق من تيليجرام (مرة واحدة فقط)
- لا تحذف ملفات `.session` — تحتوي على جلسة تسجيل الدخول
- لا ترفع `config.py` على GitHub — يحتوي على بيانات حساسة
- الكتم اليدوي يتجاوز القائمة البيضاء
