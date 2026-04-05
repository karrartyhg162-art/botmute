# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ملف الإعدادات الرئيسي لمشروع Telegram Auto-Mute Bot
# يحتوي على جميع المتغيرات اللازمة لتشغيل الـ Userbot والـ Bot
#
# ⚠️ البيانات الحساسة تُحفظ في credentials.conf
#    عدّل الملف باستخدام: nano credentials.conf
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import os
import sys

# ─── مسار ملف حفظ البيانات ───
_CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "credentials.conf")


def _load_credentials() -> dict:
    """
    تحميل بيانات الدخول من credentials.conf (ملف نصي عادي)
    كل سطر بالشكل: KEY=VALUE
    الأسطر التي تبدأ بـ # تُعتبر تعليقات وتُتجاهل
    """

    if not os.path.exists(_CREDENTIALS_FILE):
        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  ❌ ملف credentials.conf غير موجود!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()
        print("  📝 أنشئ الملف من المثال:")
        print("     cp credentials.example.conf credentials.conf")
        print()
        print("  ✏️  ثم عدّله وأدخل بياناتك:")
        print("     nano credentials.conf")
        print()
        sys.exit(1)

    creds = {}

    with open(_CREDENTIALS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # تجاهل الأسطر الفارغة والتعليقات
            if not line or line.startswith("#"):
                continue

            # تقسيم السطر عند أول =
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if value:  # فقط إذا القيمة غير فارغة
                creds[key] = value

    # ─── التحقق من البيانات المطلوبة ───
    required_keys = ["API_ID", "API_HASH", "PHONE_NUMBER", "BOT_TOKEN", "OWNER_ID"]
    missing = [k for k in required_keys if k not in creds]

    if missing:
        print()
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  ❌ بيانات ناقصة في credentials.conf!")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print()
        for k in missing:
            print(f"  ⚠️  {k} غير موجود أو فارغ")
        print()
        print("  ✏️  عدّل الملف وأكمل البيانات:")
        print("     nano credentials.conf")
        print()
        sys.exit(1)

    return creds


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# تحميل الإعدادات
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_creds = _load_credentials()

# ─── بيانات Telegram API ───
API_ID = int(_creds["API_ID"])
API_HASH = _creds["API_HASH"]

# ─── بيانات الحساب الشخصي (Userbot) ───
PHONE_NUMBER = _creds["PHONE_NUMBER"]

# اسم ملف جلسة الـ Userbot (بدون امتداد .session)
# ⚠️ هام جداً: لا تقم بتعديل هذا الاسم أبداً للحفاظ على تسجيل الدخول
SESSION_NAME = "userbot_telethon"

# ─── بيانات البوت ───
BOT_TOKEN = _creds["BOT_TOKEN"]

# ─── بيانات المالك ───
OWNER_ID = int(_creds["OWNER_ID"])

# ─── إعدادات البيانات ───
DATA_FILE = "data.json"

# ─── قائمة الاستثناءات ───
_whitelist_str = _creds.get("WHITELIST", "")
WHITELIST = []
if _whitelist_str:
    for item in _whitelist_str.split(","):
        item = item.strip()
        if item.isdigit():
            WHITELIST.append(int(item))
