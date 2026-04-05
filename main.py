# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# المشغّل الرئيسي - يشغّل الـ Userbot والـ Bot معاً
# يعمل على Termux (Android) و Linux و Windows
#
# الاستخدام:
#   python main.py
#
# أول تشغيل:
#   - سيطلب كود التحقق للحساب الشخصي في Terminal
#   - بعدها لن يطلبه مرة أخرى (الجلسة محفوظة)
#
# الإيقاف:
#   - اضغط Ctrl+C
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 👮‍♂️ ملاحظة الأمان واستمرارية الجلسة:
# لا تقم أبداً بحذف ملفات .session أو تغيير أسماء الجلسات في config.py
# لضمان عدم الحاجة لتسجيل دخول مرة أخرى.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import logging
import asyncio
import sys
import os
import signal

# لتفادي أخطاء الطباعة للغة العربية والإيموجي في Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ─── إعداد نظام التسجيل (logging) ───
# يجب أن يكون قبل أي import آخر من المشروع

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-18s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        # طباعة في Terminal
        logging.StreamHandler(sys.stdout),
        # حفظ في ملف (اختياري - مفيد لـ Termux)
        logging.FileHandler("mute_bot.log", encoding="utf-8"),
    ],
)

# تقليل إزعاج المكتبات
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.ext").setLevel(logging.WARNING)
logging.getLogger("telethon").setLevel(logging.WARNING)

logger = logging.getLogger("main")

# ─── التأكد من أن المجلد الحالي هو مجلد المشروع ───
os.chdir(os.path.dirname(os.path.abspath(__file__)))


# ─── استيراد وحدات المشروع ───
from userbot import userbot, start_userbot, stop_userbot
from bot import start_bot, stop_bot

import config


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# البانر
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BANNER = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🤖 Telegram Auto-Mute Bot
  الإصدار: 3.0.0 (Telethon)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📱 كتم تلقائي في الخاص
  👥 كتم يدوي في المجموعات
  🔧 تحكم عبر واجهة البوت
  ⚡ Telethon MTProto + HTTP Polling
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# التحقق من الإعدادات
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def validate_config() -> bool:
    """
    التحقق من أن جميع الإعدادات المطلوبة موجودة في config.py
    يُرجع True إذا كل شيء صحيح، False إذا فيه نقص
    """
    errors = []

    if not config.API_ID or config.API_ID == 0:
        errors.append("API_ID غير محدد")

    if not config.API_HASH:
        errors.append("API_HASH غير محدد")

    if not config.PHONE_NUMBER:
        errors.append("PHONE_NUMBER غير محدد")

    if not config.BOT_TOKEN:
        errors.append("BOT_TOKEN غير محدد")

    if not config.OWNER_ID or config.OWNER_ID == 0:
        errors.append("OWNER_ID غير محدد")

    if errors:
        logger.critical("❌ أخطاء في الإعدادات (config.py):")
        for err in errors:
            logger.critical(f"   • {err}")
        logger.critical("")
        logger.critical("📝 افتح config.py واملأ جميع القيم المطلوبة.")
        return False

    logger.info("✅ تم التحقق من الإعدادات بنجاح")
    return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# الدالة الرئيسية
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def main():
    """
    الدالة الرئيسية - تشغّل الـ Userbot (Telethon/MTProto)
    والـ Bot (python-telegram-bot/HTTP Polling) معاً

    ─── لماذا نستخدم مكتبتين مختلفتين؟ ───
    Telethon MTProto: ممتاز لحسابات المستخدمين (Userbot)
    يستقبل التحديثات بشكل موثوق عبر MTProto مباشرة.

    python-telegram-bot: يستخدم HTTP Long Polling الرسمي
    لاستقبال تحديثات البوت بشكل موثوق 100%.
    """
    print(BANNER)

    # ─── التحقق من الإعدادات ───
    if not validate_config():
        sys.exit(1)

    # ─── إنشاء حدث الإيقاف ───
    shutdown_event = asyncio.Event()

    # ─── تشغيل الخدمتين ───
    try:
        logger.info("جاري تشغيل الـ Userbot (Telethon MTProto)...")
        await start_userbot()

        logger.info("جاري تشغيل الـ Bot (HTTP Polling)...")
        await start_bot()

        logger.info("")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("🟢 كل شيء يعمل! البوت جاهز.")
        logger.info("   اضغط Ctrl+C للإيقاف")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("")

        # ─── الانتظار حتى Ctrl+C ───
        try:
            await shutdown_event.wait()
        except asyncio.CancelledError:
            pass

    except KeyboardInterrupt:
        logger.info("🛑 تم الإيقاف بـ Ctrl+C")

    except Exception as e:
        logger.critical(f"❌ خطأ حرج أثناء التشغيل: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # ─── إيقاف الخدمتين بشكل آمن ───
        logger.info("جاري الإيقاف الآمن...")

        try:
            await stop_bot()
        except Exception as e:
            logger.error(f"خطأ أثناء إيقاف الـ Bot: {e}")

        try:
            await stop_userbot()
        except Exception as e:
            logger.error(f"خطأ أثناء إيقاف الـ Userbot: {e}")

        logger.info("👋 تم الإيقاف بنجاح. إلى اللقاء!")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# نقطة الدخول
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    main_task = None

    def _signal_handler():
        """معالج إشارة Ctrl+C"""
        logger.info("🛑 تم استقبال Ctrl+C...")
        if main_task and not main_task.done():
            main_task.cancel()

    try:
        # تسجيل معالج Ctrl+C
        if sys.platform == "win32":
            signal.signal(signal.SIGINT, lambda s, f: _signal_handler())
        else:
            loop.add_signal_handler(signal.SIGINT, _signal_handler)
            loop.add_signal_handler(signal.SIGTERM, _signal_handler)

        main_task = loop.create_task(main())
        loop.run_until_complete(main_task)

    except KeyboardInterrupt:
        print("\n🛑 تم الإيقاف.")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"\n❌ خطأ حرج: {e}")
    finally:
        # تنظيف المهام المعلقة
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )
        except Exception:
            pass
        loop.close()
