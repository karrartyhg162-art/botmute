# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# وحدة الـ Userbot - تعمل بحساب Telegram الشخصي عبر Telethon
# المهام:
#   1. كتم تلقائي لأي شخص غريب يراسلك في الخاص + حذف رسائله
#   2. كتم يدوي في الخاص عبر لوحة التحكم + حذف رسائل المكتومين
#   3. كتم يدوي في المجموعات بأمر /mute + حذف رسائل المكتومين
#   4. إرسال إشعارات للمالك عبر Bot API
#
# ⚠️ تم استبدال pyrofork بـ Telethon لأن pyrofork كان يفشل
#    صامتاً في handle_updates() بسبب ValueError: Peer id invalid
#    مما يمنع وصول الرسائل الخاصة للمعالجات.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 👮‍♂️ ملاحظة الأمان واستمرارية الجلسة:
# لا تقم أبداً بحذف ملفات .session أو تغيير أسماء الجلسات في config.py
# لضمان عدم الحاجة لتسجيل دخول مرة أخرى.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import logging
import asyncio
import urllib.request
import urllib.parse
from datetime import datetime

from telethon import TelegramClient, events
from telethon.errors import (
    FloodWaitError,
    MessageDeleteForbiddenError,
    UserNotParticipantError,
    PeerIdInvalidError,
    RPCError,
)
from telethon.tl.types import (
    PeerUser,
    User,
)

import config
import data_manager

# إعداد نظام التسجيل
logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# إنشاء الـ Userbot Client (Telethon)
# الجلسة تُحفظ على القرص تلقائياً ولا تُحذف
# أول تشغيل → يطلب كود التحقق في Terminal
# بعدها لا يطلب كود مرة ثانية
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# استخدام اسم جلسة جديد لـ Telethon (لا نلمس جلسة pyrofork القديمة)
TELETHON_SESSION_NAME = "userbot_telethon"

userbot = TelegramClient(
    TELETHON_SESSION_NAME,
    config.API_ID,
    config.API_HASH,
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# دوال مساعدة
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def send_notification(text: str) -> None:
    """
    إرسال إشعار للمالك عبر Telegram Bot API
    يستخدم urllib من المكتبة القياسية - لا حاجة لمكتبات إضافية
    يعمل في executor لتجنب حجب event loop
    """
    try:
        url = f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage"
        payload = urllib.parse.urlencode({
            "chat_id": config.OWNER_ID,
            "text": text,
        }).encode("utf-8")

        # تنفيذ الطلب في thread منفصل لتجنب حجب الـ event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: urllib.request.urlopen(url, payload, timeout=10)
        )
        logger.debug("تم إرسال الإشعار بنجاح")

    except Exception as e:
        logger.error(f"خطأ في إرسال الإشعار: {e}")


async def safe_delete_message(client, message) -> bool:
    """
    حذف رسالة مع معالجة شاملة للأخطاء
    يستخدم Telethon client.delete_messages()

    :param client: كائن TelegramClient
    :param message: كائن الرسالة المراد حذفها
    :return: True إذا تم الحذف بنجاح، False إذا فشل
    """
    try:
        await client.delete_messages(
            message.chat_id,
            [message.id],
            revoke=True  # حذف للطرفين
        )
        return True

    except MessageDeleteForbiddenError:
        chat_id = message.chat_id
        logger.warning(f"لا توجد صلاحية حذف في المحادثة {chat_id}")
        return False

    except FloodWaitError as e:
        logger.warning(f"FloodWait أثناء الحذف: انتظار {e.seconds} ثانية...")
        await asyncio.sleep(e.seconds)
        try:
            await client.delete_messages(
                message.chat_id,
                [message.id],
                revoke=True
            )
            return True
        except Exception:
            return False

    except UserNotParticipantError:
        logger.debug("تجاهل: المستخدم ليس عضواً في المحادثة")
        return False

    except PeerIdInvalidError:
        logger.debug("تجاهل: آيدي المحادثة غير صالح")
        return False

    except RPCError as e:
        logger.debug(f"تجاهل خطأ RPC أثناء الحذف: {e}")
        return False

    except Exception as e:
        logger.error(f"خطأ غير متوقع أثناء حذف الرسالة: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# معالج الرسائل الخاصة الواردة
# يعمل على كل رسالة خاصة جديدة تصل للحساب
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def handle_private_message(event):
    """
    معالجة الرسائل الخاصة الواردة:
    - إذا المرسل مكتوم يدوياً → حذف رسالته فوراً (أولوية عليا)
    - إذا المرسل مكتوم تلقائياً → حذف رسالته فوراً
    - إذا المرسل في القائمة البيضاء → تجاهل
    - إذا المرسل غريب → كتمه + حذف رسالته + إشعار
    """
    try:
        message = event.message
        client = event.client

        # ─── التحقق الأساسي ───
        if not message or not message.sender_id:
            return

        sender_id = message.sender_id

        # تجاهل الرسائل الصادرة (رسائلك أنت)
        if message.out:
            return

        # ─── جلب معلومات المرسل ───
        sender = await event.get_sender()
        if not sender:
            logger.debug(f"لم يتم العثور على المرسل {sender_id}")
            return

        # تجاهل رسائل البوتات
        if getattr(sender, 'bot', False):
            return

        # تجاهل رسائل المالك (أنت)
        if sender_id == config.OWNER_ID:
            return

        username = getattr(sender, 'username', '') or ''
        first_name = getattr(sender, 'first_name', '') or ''
        last_name = getattr(sender, 'last_name', '') or ''

        logger.info(
            f"📩 [DM] رسالة خاصة واردة | "
            f"المرسل: {sender_id} (@{username}) ({first_name} {last_name}) | "
            f"نص: {(message.text or '')[0:50]}..."
        )

        # ─── قراءة قوائم الكتم من data.json (بدون cache) ───
        data = data_manager.load_data()
        dm_muted_manual = data.get("dm_mute_manual", [])
        dm_muted_auto = data.get("dm_muted", [])
        whitelist_dynamic = data.get("whitelist", [])
        whitelist_static = getattr(config, 'WHITELIST', [])

        logger.info(
            f"   📋 قوائم الكتم: يدوي={dm_muted_manual} | تلقائي={dm_muted_auto} | "
            f"قائمة بيضاء (ثابت)={whitelist_static} | قائمة بيضاء (دينام.)={whitelist_dynamic}"
        )

        # ─── أولوية 1: الكتم اليدوي (يتجاوز القائمة البيضاء) ───
        if sender_id in dm_muted_manual:
            logger.info(f"   🔇 المرسل {sender_id} موجود في قائمة الكتم اليدوي → جاري الحذف...")
            deleted = await safe_delete_message(client, message)
            logger.info(
                f"   🔇 حذف رسالة من المكتوم يدوياً {sender_id} (@{username}) "
                f"- نتيجة الحذف: {'✅ نجح' if deleted else '❌ فشل'}"
            )
            return

        # ─── أولوية 2: الكتم التلقائي ───
        if sender_id in dm_muted_auto:
            logger.info(f"   🔇 المرسل {sender_id} موجود في قائمة الكتم التلقائي → جاري الحذف...")
            deleted = await safe_delete_message(client, message)
            logger.info(
                f"   🔇 حذف رسالة من المكتوم تلقائياً {sender_id} (@{username}) "
                f"- نتيجة الحذف: {'✅ نجح' if deleted else '❌ فشل'}"
            )
            return

        # ─── أولوية 3: القائمة البيضاء ───
        if sender_id in whitelist_static or sender_id in whitelist_dynamic:
            logger.debug(f"   ✅ تجاهل رسالة من المستثنى {sender_id} (قائمة بيضاء)")
            return

        # ─── الحالة الأخيرة: مرسل جديد (أول رسالة) - كتم تلقائي ───
        logger.info(f"   🆕 مرسل جديد {sender_id} → كتم تلقائي + حذف...")
        data_manager.add_dm_mute(sender_id)
        deleted = await safe_delete_message(client, message)

        # تجهيز بيانات الإشعار
        username_display = f"@{username}" if username else "بدون يوزر"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        logger.info(
            f"   ✅ تم كتم المستخدم {sender_id} ({first_name} {last_name}) في الخاص تلقائياً"
            f" | حذف: {'✅' if deleted else '❌'}"
        )

        # إرسال إشعار للمالك عبر البوت
        notification = (
            f"🔇 تم كتم في الخاص\n"
            f"👤 الاسم: {first_name} {last_name}\n"
            f"🆔 الآيدي: {sender_id}\n"
            f"📎 اليوزر: {username_display}\n"
            f"📅 الوقت: {timestamp}"
        )
        await send_notification(notification)

    except FloodWaitError as e:
        logger.warning(f"FloodWait في معالجة الخاص: انتظار {e.seconds} ثانية...")
        await asyncio.sleep(e.seconds)
    except RPCError as e:
        logger.error(f"خطأ RPC في معالجة الرسالة الخاصة: {e}")
    except Exception as e:
        logger.error(f"خطأ غير متوقع في معالجة الرسالة الخاصة: {e}")
        import traceback
        traceback.print_exc()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# معالج أوامر الكتم في المجموعات (/mute & /unmute)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def handle_mute_command(event):
    """
    أمر /mute في المجموعة
    الاستخدام: رد على رسالة شخص ثم اكتب /mute
    الشروط: فقط المالك يقدر يستخدمه، لازم يكون رد على رسالة
    """
    try:
        message = event.message
        client = event.client

        # ─── التحقق: لازم يكون رد على رسالة ───
        if not message.reply_to_msg_id:
            await safe_delete_message(client, message)
            return

        # ─── جلب الرسالة المردود عليها ───
        replied = await message.get_reply_message()
        if not replied or not replied.sender_id:
            await safe_delete_message(client, message)
            return

        target_id = replied.sender_id

        # لا يمكن كتم نفسك
        if target_id == config.OWNER_ID:
            await safe_delete_message(client, message)
            return

        group_id = message.chat_id
        chat = await event.get_chat()
        group_title = getattr(chat, 'title', '') or "بدون عنوان"

        # ─── إضافة المستهدف لقائمة الكتم ───
        added = data_manager.add_group_mute(group_id, target_id)

        # حذف رسالة الأمر /mute
        await safe_delete_message(client, message)

        # حذف رسالة الشخص المستهدف
        await safe_delete_message(client, replied)

        if added:
            target_user = await client.get_entity(target_id)
            first_name = getattr(target_user, 'first_name', '') or ''
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            logger.info(
                f"تم كتم {target_id} ({first_name}) في المجموعة "
                f"{group_id} ({group_title})"
            )

            # إرسال إشعار للمالك
            notification = (
                f"🔇 تم كتم في مجموعة\n"
                f"👤 الاسم: {first_name}\n"
                f"🆔 الآيدي: {target_id}\n"
                f"🏘️ المجموعة: {group_title}\n"
                f"📅 الوقت: {timestamp}"
            )
            await send_notification(notification)
        else:
            logger.debug(
                f"المستخدم {target_id} مكتوم مسبقاً في المجموعة {group_id}"
            )

    except FloodWaitError as e:
        logger.warning(f"FloodWait في أمر الكتم: انتظار {e.seconds} ثانية...")
        await asyncio.sleep(e.seconds)
    except RPCError as e:
        logger.error(f"خطأ RPC في أمر الكتم: {e}")
    except Exception as e:
        logger.error(f"خطأ غير متوقع في أمر الكتم: {e}")


async def handle_unmute_command(event):
    """
    أمر /unmute في المجموعة
    الاستخدام: رد على رسالة شخص مكتوم ثم اكتب /unmute
    """
    try:
        message = event.message
        client = event.client

        # ─── التحقق: لازم يكون رد على رسالة ───
        if not message.reply_to_msg_id:
            await safe_delete_message(client, message)
            return

        # ─── جلب الرسالة المردود عليها ───
        replied = await message.get_reply_message()
        if not replied or not replied.sender_id:
            await safe_delete_message(client, message)
            return

        target_id = replied.sender_id

        # لا يمكن إلغاء كتم نفسك
        if target_id == config.OWNER_ID:
            await safe_delete_message(client, message)
            return

        group_id = message.chat_id
        chat = await event.get_chat()
        group_title = getattr(chat, 'title', '') or "بدون عنوان"

        # ─── إزالة المستهدف من قائمة الكتم ───
        removed = data_manager.remove_group_mute(group_id, target_id)

        # حذف رسالة الأمر /unmute
        await safe_delete_message(client, message)

        if removed:
            target_user = await client.get_entity(target_id)
            first_name = getattr(target_user, 'first_name', '') or ''

            logger.info(
                f"تم إلغاء كتم {target_id} ({first_name}) في المجموعة "
                f"{group_id} ({group_title})"
            )

            # إرسال إشعار للمالك
            notification = (
                f"🔊 تم إلغاء كتم في مجموعة\n"
                f"👤 الاسم: {first_name}\n"
                f"🆔 الآيدي: {target_id}\n"
                f"🏘️ المجموعة: {group_title}"
            )
            await send_notification(notification)
        else:
            logger.debug(
                f"المستخدم {target_id} غير مكتوم أصلاً في المجموعة {group_id}"
            )

    except FloodWaitError as e:
        logger.warning(f"FloodWait في إلغاء الكتم: انتظار {e.seconds} ثانية...")
        await asyncio.sleep(e.seconds)
    except RPCError as e:
        logger.error(f"خطأ RPC في إلغاء الكتم: {e}")
    except Exception as e:
        logger.error(f"خطأ غير متوقع في إلغاء الكتم: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# معالج رسائل المكتومين في المجموعات (حذف تلقائي)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def handle_group_message(event):
    """
    حذف رسائل المكتومين تلقائياً في المجموعات
    """
    try:
        message = event.message
        client = event.client

        if not message.sender_id:
            return

        sender_id = message.sender_id

        # تجاهل الرسائل الصادرة
        if message.out:
            return

        # تجاهل رسائل البوتات
        sender = await event.get_sender()
        if sender and getattr(sender, 'bot', False):
            return

        group_id = message.chat_id

        # التحقق إذا المرسل مكتوم في هذه المجموعة
        if data_manager.is_group_muted(group_id, sender_id):
            deleted = await safe_delete_message(client, message)
            logger.info(
                f"🔇 حذف رسالة من {sender_id} في المجموعة {group_id} "
                f"- نتيجة: {'✅' if deleted else '❌'}"
            )

    except FloodWaitError as e:
        logger.warning(
            f"FloodWait في حذف رسالة مجموعة: انتظار {e.seconds} ثانية..."
        )
        await asyncio.sleep(e.seconds)
    except RPCError as e:
        logger.error(f"خطأ RPC في معالجة رسالة المجموعة: {e}")
    except Exception as e:
        logger.error(f"خطأ غير متوقع في معالجة رسالة المجموعة: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# تسجيل المعالجات وتشغيل الـ Userbot
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def register_handlers():
    """
    تسجيل جميع معالجات الأحداث مع Telethon
    يتم التسجيل قبل تشغيل العميل
    """
    logger.info("جاري تسجيل معالجات Telethon...")

    # ─── معالج الرسائل الخاصة الواردة ───
    # incoming=True: رسائل واردة فقط (ليست صادرة)
    # func=lambda e: e.is_private: رسائل خاصة فقط
    userbot.add_event_handler(
        handle_private_message,
        events.NewMessage(incoming=True, func=lambda e: e.is_private)
    )
    logger.info("   ✅ تم تسجيل: handle_private_message (private & incoming)")

    # ─── معالج أمر /mute في المجموعات ───
    userbot.add_event_handler(
        handle_mute_command,
        events.NewMessage(
            outgoing=True,  # أوامرك أنت فقط
            pattern=r'^/mute$',
            func=lambda e: e.is_group or e.is_channel
        )
    )
    logger.info("   ✅ تم تسجيل: handle_mute_command (group, outgoing, /mute)")

    # ─── معالج أمر /unmute في المجموعات ───
    userbot.add_event_handler(
        handle_unmute_command,
        events.NewMessage(
            outgoing=True,
            pattern=r'^/unmute$',
            func=lambda e: e.is_group or e.is_channel
        )
    )
    logger.info("   ✅ تم تسجيل: handle_unmute_command (group, outgoing, /unmute)")

    # ─── معالج رسائل المكتومين في المجموعات ───
    userbot.add_event_handler(
        handle_group_message,
        events.NewMessage(
            incoming=True,
            func=lambda e: e.is_group or e.is_channel
        )
    )
    logger.info("   ✅ تم تسجيل: handle_group_message (group & incoming)")

    logger.info("✅ تم تسجيل جميع المعالجات بنجاح!")


async def start_userbot() -> None:
    """
    تشغيل الـ Userbot (Telethon)
    - يسجل المعالجات أولاً
    - يبدأ اتصال Telethon بحساب Telegram الشخصي
    - أول مرة: يطلب كود التحقق في Terminal
    - بعدها: يستخدم الجلسة المحفوظة على القرص
    """
    try:
        # ─── تسجيل المعالجات قبل التشغيل ───
        register_handlers()

        # ─── تشغيل العميل ───
        logger.info("جاري الاتصال بـ Telegram (Telethon)...")
        await userbot.start(phone=config.PHONE_NUMBER)

        me = await userbot.get_me()

        logger.info(
            f"✅ تم تشغيل الـ Userbot بنجاح: "
            f"{me.first_name} (@{me.username or 'بدون يوزر'}) "
            f"[ID: {me.id}]"
        )
        print(
            f"✅ تم تشغيل الـ Userbot: "
            f"{me.first_name} (@{me.username or 'بدون يوزر'})"
        )

        # ─── تشخيص: عرض قوائم الكتم الحالية ───
        dm_muted = data_manager.get_dm_muted()
        dm_manual = data_manager.get_dm_mute_manual()
        data_obj = data_manager.load_data()
        group_muted = data_obj.get("group_muted", {})

        logger.info(f"📋 قائمة المكتومين تلقائياً في الخاص ({len(dm_muted)}): {dm_muted}")
        logger.info(f"📋 قائمة المكتومين يدوياً في الخاص ({len(dm_manual)}): {dm_manual}")
        logger.info(f"📋 المجموعات المفعّل فيها الكتم: {len(group_muted)}")
        logger.info(f"📋 القائمة البيضاء الثابتة (config): {config.WHITELIST}")
        logger.info(f"📋 القائمة البيضاء الديناميكية (data.json): {data_manager.get_whitelist()}")
        logger.info(
            "⚠️ ملاحظة: الكتم اليدوي يتجاوز القائمة البيضاء - "
            "إذا شخص مكتوم يدوياً وموجود بالقائمة البيضاء، رسائله ستُحذف."
        )

        # ─── تشخيص: المعالجات المسجلة ───
        handler_count = len(userbot.list_event_handlers())
        logger.info(f"📋 عدد المعالجات المسجلة: {handler_count}")
        for callback, event_filter in userbot.list_event_handlers():
            handler_name = getattr(callback, '__name__', str(callback))
            event_type = type(event_filter).__name__ if event_filter else 'None'
            logger.info(f"   Handler: {handler_name} ({event_type})")

    except Exception as e:
        logger.critical(f"❌ فشل تشغيل الـ Userbot: {e}")
        import traceback
        traceback.print_exc()
        raise


async def stop_userbot() -> None:
    """إيقاف الـ Userbot بشكل آمن"""
    try:
        if userbot.is_connected():
            await userbot.disconnect()
            logger.info("تم إيقاف الـ Userbot بنجاح")
    except Exception as e:
        logger.error(f"خطأ أثناء إيقاف الـ Userbot: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# تشغيل مستقل (للاختبار فقط)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    # إعداد logging للاختبار المستقل
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async def _test_run():
        """تشغيل اختباري مستقل"""
        await start_userbot()
        logger.info("الـ Userbot يعمل... اضغط Ctrl+C للإيقاف")
        try:
            # البقاء في وضع التشغيل
            await userbot.run_until_disconnected()
        except KeyboardInterrupt:
            pass
        finally:
            await stop_userbot()

    asyncio.run(_test_run())
