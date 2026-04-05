# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# وحدة الـ Bot - واجهة التحكم عبر بوت Telegram
# تستخدم python-telegram-bot مع HTTP Long Polling
# الـ Userbot يعمل بـ Telethon (لتحويل الـ username إلى ID)
#
# يعمل بـ bot_token ومتاح فقط لـ OWNER_ID
# المهام:
#   1. عرض قوائم المكتومين (خاص + مجموعات)
#   2. إلغاء كتم من الواجهة
#   3. إدارة القائمة البيضاء
#   4. عرض المساعدة والإحصائيات
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import logging
import asyncio

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Bot,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import BadRequest, TelegramError

import config
import data_manager
from userbot import userbot

# إعداد نظام التسجيل
logger = logging.getLogger(__name__)

# عدد العناصر في كل صفحة (للتقسيم)
ITEMS_PER_PAGE = 8

# حالات المستخدمين لتتبع المدخلات المنتظرة
_user_states: dict = {}

# مرجع لـ Application لاستخدامه في التشغيل والإيقاف
app: Application = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# دوال مساعدة
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def get_user_name(bot_instance: Bot, user_id: int) -> str:
    """محاولة جلب اسم المستخدم من آيديه عبر Bot API"""
    try:
        chat = await bot_instance.get_chat(user_id)
        name = chat.first_name or ""
        if chat.last_name:
            name += f" {chat.last_name}"
        return name.strip() or str(user_id)
    except Exception:
        return str(user_id)


async def get_group_name(bot_instance: Bot, group_id: int) -> str:
    """محاولة جلب اسم المجموعة من آيديها"""
    try:
        chat = await bot_instance.get_chat(group_id)
        return chat.title or str(group_id)
    except Exception:
        return str(group_id)


def build_start_keyboard() -> InlineKeyboardMarkup:
    """بناء لوحة مفاتيح القائمة الرئيسية"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📋 قائمة مكتومين الخاص", callback_data="dm_mute_list"
            ),
            InlineKeyboardButton(
                "📋 قائمة مكتومين المجموعات", callback_data="group_mute_list"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔇 كتم يوزر في الخاص", callback_data="manual_dm_mute_menu"
            ),
        ],
        [
            InlineKeyboardButton(
                "➕ إضافة للقائمة البيضاء", callback_data="add_whitelist"
            ),
            InlineKeyboardButton(
                "📄 القائمة البيضاء", callback_data="show_whitelist"
            ),
        ],
        [
            InlineKeyboardButton("ℹ️ المساعدة", callback_data="help"),
        ],
    ])


def build_start_text() -> str:
    """بناء نص القائمة الرئيسية مع الإحصائيات"""
    dm_count = len(data_manager.get_dm_muted())
    manual_dm_count = len(data_manager.get_dm_mute_manual())
    data_obj = data_manager.load_data()
    group_count = len(data_obj.get("group_muted", {}))

    return (
        "🤖 مرحباً! أنا بوت الكتم التلقائي.\n\n"
        "📌 الوظائف:\n"
        "• كتم تلقائي لأي شخص غريب يراسلك في الخاص\n"
        "• كتم يدوي في المجموعات بأمر /mute\n"
        "• كتم يوزر في الخاص (حذف رسائله فقط)\n"
        "• حذف رسائل المكتومين فوراً\n\n"
        f"📊 الحالة:\n"
        f"• عدد المكتومين في الخاص (تلقائي): {dm_count}\n"
        f"• عدد المكتومين في الخاص (يدوي): {manual_dm_count}\n"
        f"• عدد المجموعات المفعّل فيها الكتم: {group_count}\n\n"
        "اختر من القائمة:"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# أمر /start
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة أمر /start"""
    user_id = update.effective_user.id if update.effective_user else None
    logger.info(f"🚀 [START] تم استقبال /start من المستخدم {user_id}")

    # التحقق من المالك
    if user_id != config.OWNER_ID:
        logger.warning(
            f"⛔ [START] رفض: المستخدم {user_id} ليس المالك ({config.OWNER_ID})"
        )
        await update.message.reply_text("⛔ هذا البوت خاص ولا يمكنك استخدامه.")
        return

    try:
        # إلغاء أي حالة انتظار سابقة
        _user_states.pop(config.OWNER_ID, None)

        text = build_start_text()
        keyboard = build_start_keyboard()
        logger.info("🚀 [START] جاري إرسال القائمة الرئيسية للمالك...")

        await update.message.reply_text(text, reply_markup=keyboard)
        logger.info("✅ [START] تم إرسال القائمة الرئيسية بنجاح")

    except TelegramError as e:
        logger.error(f"❌ [START] خطأ Telegram: {e}")
        try:
            await update.message.reply_text("❌ حدث خطأ. حاول مرة أخرى.")
        except Exception:
            pass

    except Exception as e:
        logger.error(f"❌ [START] خطأ غير متوقع: {type(e).__name__}: {e}")
        try:
            await update.message.reply_text("❌ حدث خطأ. حاول مرة أخرى.")
        except Exception:
            pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# معالج جميع الأزرار (Callback Query)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة جميع ضغطات الأزرار الـ Inline"""
    callback_query = update.callback_query

    # ─── التحقق من المالك ───
    if callback_query.from_user.id != config.OWNER_ID:
        await callback_query.answer(
            "⛔ غير مصرح لك باستخدام هذا البوت", show_alert=True
        )
        return

    data = callback_query.data
    logger.info(f"🔘 [CALLBACK] ضغط زر: {data}")
    bot_instance = context.bot

    try:
        # إلغاء حالة الانتظار عند أي ضغطة زر (ما عدا noop)
        if data != "noop":
            _user_states.pop(config.OWNER_ID, None)

        # ─── توجيه حسب نوع الزر ───
        if data == "back_to_start":
            await _show_start_menu(callback_query)

        elif data == "dm_mute_list":
            await _show_dm_mute_list(bot_instance, callback_query, page=0)

        elif data.startswith("dm_page_"):
            page = int(data[len("dm_page_"):])
            await _show_dm_mute_list(bot_instance, callback_query, page=page)

        elif data.startswith("unmute_dm_"):
            user_id = int(data[len("unmute_dm_"):])
            await _unmute_dm(bot_instance, callback_query, user_id)

        elif data == "group_mute_list":
            await _show_group_mute_list(bot_instance, callback_query)

        elif data.startswith("group_detail_"):
            group_id = int(data[len("group_detail_"):])
            await _show_group_detail(bot_instance, callback_query, group_id)

        elif data.startswith("unmute_group_"):
            rest = data[len("unmute_group_"):]
            gid_str, uid_str = rest.rsplit("_", 1)
            await _unmute_group(
                bot_instance, callback_query, int(gid_str), int(uid_str)
            )

        elif data == "add_whitelist":
            await _add_whitelist_prompt(callback_query)

        elif data == "show_whitelist":
            await _show_whitelist(bot_instance, callback_query)

        elif data.startswith("remove_wl_"):
            user_id = int(data[len("remove_wl_"):])
            await _remove_whitelist(bot_instance, callback_query, user_id)

        elif data == "manual_dm_mute_menu":
            await _show_manual_dm_mute_menu(bot_instance, callback_query)

        elif data == "add_manual_dm_mute":
            await _add_manual_dm_mute_prompt(callback_query)

        elif data == "show_manual_dm_list":
            await _show_manual_dm_mute_list(bot_instance, callback_query, page=0)

        elif data.startswith("manual_dm_page_"):
            page = int(data[len("manual_dm_page_"):])
            await _show_manual_dm_mute_list(bot_instance, callback_query, page=page)

        elif data.startswith("unmute_manual_dm_"):
            user_id = int(data[len("unmute_manual_dm_"):])
            await _unmute_manual_dm(bot_instance, callback_query, user_id)

        elif data == "help":
            await _show_help(callback_query)

        elif data == "noop":
            await callback_query.answer()

        else:
            await callback_query.answer("⚠️ أمر غير معروف")

    except BadRequest as e:
        err_msg = str(e)
        if "Message is not modified" in err_msg:
            # المستخدم ضغط نفس الزر مرتين → تجاهل
            await callback_query.answer()
        elif "Message to edit not found" in err_msg or "message can't be edited" in err_msg:
            # الرسالة لم تعد موجودة → أرسل رسالة جديدة
            try:
                await callback_query.message.reply_text(
                    "⚠️ انتهت صلاحية الرسالة. أرسل /start من جديد."
                )
            except Exception:
                pass
        else:
            logger.error(f"خطأ BadRequest في الـ Callback: {e}")
            await callback_query.answer("❌ حدث خطأ", show_alert=True)

    except TelegramError as e:
        logger.error(f"خطأ Telegram في الـ Callback: {e}")
        await callback_query.answer("❌ حدث خطأ", show_alert=True)

    except Exception as e:
        logger.error(f"خطأ غير متوقع في الـ Callback [{data}]: {e}")
        await callback_query.answer("❌ حدث خطأ غير متوقع", show_alert=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# الوظائف الداخلية لكل زر
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def _show_start_menu(cq):
    """العودة للقائمة الرئيسية"""
    await cq.edit_message_text(
        build_start_text(), reply_markup=build_start_keyboard()
    )
    await cq.answer()


# ────── قائمة مكتومين الخاص ──────


async def _show_dm_mute_list(bot_instance, cq, page: int = 0):
    """عرض قائمة المكتومين في الخاص مع تقسيم صفحات"""
    muted = data_manager.get_dm_muted()

    if not muted:
        await cq.edit_message_text(
            "📋 لا يوجد مكتومين في الخاص حالياً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")]
            ]),
        )
        await cq.answer()
        return

    total = len(muted)
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(0, min(page, total_pages - 1))

    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total)
    page_items = muted[start_idx:end_idx]

    text = f"📋 قائمة المكتومين في الخاص ({total}):\n\n"
    buttons = []

    for i, uid in enumerate(page_items, start=start_idx + 1):
        name = await get_user_name(bot_instance, uid)
        text += f"{i}. 👤 {name} - {uid}\n"
        buttons.append([
            InlineKeyboardButton(
                f"🔊 إلغاء كتم {name}",
                callback_data=f"unmute_dm_{uid}",
            )
        ])

    # أزرار التنقل بين الصفحات
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(
                "⬅️ السابق", callback_data=f"dm_page_{page - 1}"
            ))
        nav.append(InlineKeyboardButton(
            f"صفحة {page + 1}/{total_pages}", callback_data="noop"
        ))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(
                "➡️ التالي", callback_data=f"dm_page_{page + 1}"
            ))
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")
    ])

    await cq.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(buttons)
    )
    await cq.answer()


async def _unmute_dm(bot_instance, cq, user_id: int):
    """إلغاء كتم مستخدم في الخاص"""
    name = await get_user_name(bot_instance, user_id)
    removed = data_manager.remove_dm_mute(user_id)

    if removed:
        text = f"✅ تم إلغاء كتم {name} ({user_id}) من الخاص"
        logger.info(f"تم إلغاء كتم {user_id} من الخاص عبر البوت")
    else:
        text = f"⚠️ المستخدم {name} ({user_id}) غير موجود في قائمة الكتم"

    await cq.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔙 رجوع للقائمة", callback_data="dm_mute_list"
            )]
        ]),
    )
    await cq.answer()


# ────── قائمة مكتومين المجموعات ──────


async def _show_group_mute_list(bot_instance, cq):
    """عرض المجموعات التي فيها مكتومين"""
    data_obj = data_manager.load_data()
    group_muted = data_obj.get("group_muted", {})

    if not group_muted:
        await cq.edit_message_text(
            "📋 لا يوجد مكتومين في أي مجموعة حالياً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")]
            ]),
        )
        await cq.answer()
        return

    text = "📋 المجموعات المفعّل فيها الكتم:\n\n"
    buttons = []

    for i, (gid_str, users) in enumerate(group_muted.items(), 1):
        gid = int(gid_str)
        gname = await get_group_name(bot_instance, gid)
        count = len(users)
        text += f"{i}. 🏘️ {gname} ({count} مكتوم)\n"
        buttons.append([
            InlineKeyboardButton(
                f"🏘️ {gname}", callback_data=f"group_detail_{gid_str}"
            )
        ])

    buttons.append([
        InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")
    ])

    await cq.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(buttons)
    )
    await cq.answer()


async def _show_group_detail(bot_instance, cq, group_id: int):
    """عرض المكتومين في مجموعة محددة مع أزرار إلغاء الكتم"""
    gname = await get_group_name(bot_instance, group_id)
    muted = data_manager.get_group_muted(group_id)

    if not muted:
        await cq.edit_message_text(
            f"📋 لا يوجد مكتومين في المجموعة {gname}.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 رجوع للمجموعات", callback_data="group_mute_list"
                )]
            ]),
        )
        await cq.answer()
        return

    text = f"📋 المكتومين في {gname} ({len(muted)}):\n\n"
    buttons = []

    for i, uid in enumerate(muted, 1):
        name = await get_user_name(bot_instance, uid)
        text += f"{i}. 👤 {name} - {uid}\n"
        buttons.append([
            InlineKeyboardButton(
                f"🔊 إلغاء كتم {name}",
                callback_data=f"unmute_group_{group_id}_{uid}",
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            "🔙 رجوع للمجموعات", callback_data="group_mute_list"
        )
    ])

    await cq.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(buttons)
    )
    await cq.answer()


async def _unmute_group(bot_instance, cq, group_id: int, user_id: int):
    """إلغاء كتم مستخدم في مجموعة محددة"""
    name = await get_user_name(bot_instance, user_id)
    gname = await get_group_name(bot_instance, group_id)
    removed = data_manager.remove_group_mute(group_id, user_id)

    if removed:
        text = f"✅ تم إلغاء كتم {name} ({user_id}) من المجموعة {gname}"
        logger.info(
            f"تم إلغاء كتم {user_id} من المجموعة {group_id} عبر البوت"
        )
    else:
        text = f"⚠️ المستخدم {name} ({user_id}) غير مكتوم في {gname}"

    await cq.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔙 رجوع للمجموعة",
                callback_data=f"group_detail_{group_id}",
            )]
        ]),
    )
    await cq.answer()


# ────── القائمة البيضاء ──────


async def _add_whitelist_prompt(cq):
    """طلب إدخال آيدي لإضافته للقائمة البيضاء"""
    _user_states[config.OWNER_ID] = "waiting_whitelist"

    text = (
        "➕ إضافة للقائمة البيضاء\n\n"
        "أرسل آيدي أو يوزر المستخدم لإضافته للقائمة البيضاء:\n\n"
        "💡 مثال: @username أو 123456789"
    )

    await cq.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ إلغاء", callback_data="back_to_start")]
        ]),
    )
    await cq.answer()


async def _show_whitelist(bot_instance, cq):
    """عرض القائمة البيضاء مع أزرار إزالة"""
    # دمج القائمة من data.json مع config.py
    dynamic_wl = data_manager.get_whitelist()
    static_wl = getattr(config, "WHITELIST", [])
    all_wl = list(dict.fromkeys(dynamic_wl + static_wl))  # إزالة التكرار

    if not all_wl:
        await cq.edit_message_text(
            "📄 القائمة البيضاء فارغة حالياً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")]
            ]),
        )
        await cq.answer()
        return

    text = f"📄 القائمة البيضاء ({len(all_wl)}):\n\n"
    buttons = []

    for i, uid in enumerate(all_wl, 1):
        name = await get_user_name(bot_instance, uid)
        # تحديد المصدر (ثابت من config أو ديناميكي من data.json)
        if uid in static_wl and uid not in dynamic_wl:
            source = " (ثابت)"
        else:
            source = ""
        text += f"{i}. 👤 {name} - {uid}{source}\n"

        # زر الإزالة فقط للعناصر الديناميكية
        if uid in dynamic_wl:
            buttons.append([
                InlineKeyboardButton(
                    f"❌ إزالة {name}", callback_data=f"remove_wl_{uid}"
                )
            ])

    buttons.append([
        InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")
    ])

    await cq.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(buttons)
    )
    await cq.answer()


async def _remove_whitelist(bot_instance, cq, user_id: int):
    """إزالة مستخدم من القائمة البيضاء"""
    name = await get_user_name(bot_instance, user_id)
    removed = data_manager.remove_whitelist(user_id)

    if removed:
        text = f"✅ تم إزالة {name} ({user_id}) من القائمة البيضاء"
        logger.info(f"تم إزالة {user_id} من القائمة البيضاء عبر البوت")
    else:
        text = f"⚠️ المستخدم {name} ({user_id}) غير موجود في القائمة البيضاء"

    await cq.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔙 رجوع للقائمة", callback_data="show_whitelist"
            )]
        ]),
    )
    await cq.answer()


# ────── كتم يوزر في الخاص (يدوي) ──────


async def _show_manual_dm_mute_menu(bot_instance, cq):
    """عرض قائمة كتم الخاص اليدوي"""
    manual_count = len(data_manager.get_dm_mute_manual())

    text = (
        "🔇 كتم يوزر في الخاص\n\n"
        "هذه الميزة تتيح لك كتم شخص معين في الخاص.\n"
        "أي رسالة جديدة تأتي منه ستُحذف تلقائياً،\n"
        "وتبقى فقط رسائلك في المحادثة.\n\n"
        f"📊 عدد المكتومين حالياً: {manual_count}\n\n"
        "اختر:"
    )

    buttons = [
        [
            InlineKeyboardButton(
                "➕ إضافة يوزر للكتم", callback_data="add_manual_dm_mute"
            ),
        ],
        [
            InlineKeyboardButton(
                "📋 عرض قائمة المكتومين", callback_data="show_manual_dm_list"
            ),
        ],
        [
            InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start"),
        ],
    ]

    await cq.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    await cq.answer()


async def _add_manual_dm_mute_prompt(cq):
    """طلب إدخال آيدي لإضافته لقائمة كتم الخاص اليدوي"""
    _user_states[config.OWNER_ID] = "waiting_manual_dm_mute"

    text = (
        "🔇 إضافة يوزر للكتم في الخاص\n\n"
        "أرسل آيدي أو يوزر المستخدم الذي تريد كتمه:\n\n"
        "💡 مثال: @username أو 123456789\n"
        "⚠️ سيتم حذف جميع رسائله الجديدة تلقائياً"
    )

    await cq.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ إلغاء", callback_data="manual_dm_mute_menu")]
        ]),
    )
    await cq.answer()


async def _show_manual_dm_mute_list(bot_instance, cq, page: int = 0):
    """عرض قائمة المكتومين يدوياً في الخاص مع تقسيم صفحات"""
    muted = data_manager.get_dm_mute_manual()

    if not muted:
        await cq.edit_message_text(
            "📋 لا يوجد مكتومين يدوياً في الخاص حالياً.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="manual_dm_mute_menu")]
            ]),
        )
        await cq.answer()
        return

    total = len(muted)
    total_pages = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
    page = max(0, min(page, total_pages - 1))

    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total)
    page_items = muted[start_idx:end_idx]

    text = f"🔇 المكتومين يدوياً في الخاص ({total}):\n\n"
    buttons = []

    for i, uid in enumerate(page_items, start=start_idx + 1):
        name = await get_user_name(bot_instance, uid)
        text += f"{i}. 👤 {name} - {uid}\n"
        buttons.append([
            InlineKeyboardButton(
                f"🔊 إلغاء كتم {name}",
                callback_data=f"unmute_manual_dm_{uid}",
            )
        ])

    # أزرار التنقل بين الصفحات
    if total_pages > 1:
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton(
                "⬅️ السابق", callback_data=f"manual_dm_page_{page - 1}"
            ))
        nav.append(InlineKeyboardButton(
            f"صفحة {page + 1}/{total_pages}", callback_data="noop"
        ))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton(
                "➡️ التالي", callback_data=f"manual_dm_page_{page + 1}"
            ))
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton("🔙 رجوع", callback_data="manual_dm_mute_menu")
    ])

    await cq.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(buttons)
    )
    await cq.answer()


async def _unmute_manual_dm(bot_instance, cq, user_id: int):
    """إلغاء كتم مستخدم من قائمة الكتم اليدوي في الخاص"""
    name = await get_user_name(bot_instance, user_id)
    removed = data_manager.remove_dm_mute_manual(user_id)

    if removed:
        text = f"✅ تم إلغاء كتم {name} ({user_id}) من الخاص"
        logger.info(f"تم إلغاء كتم يدوي {user_id} من الخاص عبر البوت")
    else:
        text = f"⚠️ المستخدم {name} ({user_id}) غير موجود في قائمة الكتم اليدوي"

    await cq.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔙 رجوع للقائمة", callback_data="show_manual_dm_list"
            )]
        ]),
    )
    await cq.answer()


# ────── المساعدة ──────


async def _show_help(cq):
    """عرض صفحة المساعدة"""
    text = (
        "ℹ️ طريقة الاستخدام:\n\n"
        "📱 الرسائل الخاصة:\n"
        "• الكتم تلقائي - أي شخص غريب يراسلك يُكتم فوراً\n"
        "• رسائله تُحذف تلقائياً\n"
        "• يمكنك إلغاء كتمه من القائمة\n\n"
        "🔇 كتم يوزر في الخاص:\n"
        "• أضف آيدي أي شخص لحذف رسائله الجديدة تلقائياً\n"
        "• تبقى فقط رسائلك في المحادثة معه\n"
        "• يمكنك إلغاء الكتم في أي وقت\n\n"
        "👥 المجموعات:\n"
        "• رد على رسالة الشخص واكتب /mute لكتمه\n"
        "• رد على رسالته واكتب /unmute لإلغاء كتمه\n"
        "• الكتم خاص بكل مجموعة على حدة\n\n"
        "⚠️ ملاحظات:\n"
        "• يجب أن يكون حسابك أدمن في المجموعة لحذف الرسائل\n"
        "• القائمة البيضاء تمنع الكتم التلقائي في الخاص فقط"
    )

    await cq.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_start")]
        ]),
    )
    await cq.answer()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# معالج النصوص - لإدخالات القائمة البيضاء
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل النصية (لإدخال آيدي القائمة البيضاء)"""
    message = update.message
    if not message or not message.text:
        return

    # تجاهل الأوامر
    if message.text.startswith("/"):
        return

    user_id = update.effective_user.id

    # رفض غير المالك
    if user_id != config.OWNER_ID:
        await message.reply_text("⛔ هذا البوت خاص ولا يمكنك استخدامه.")
        return

    state = _user_states.get(config.OWNER_ID)
    bot_instance = context.bot

    if state == "waiting_whitelist":
        # إزالة حالة الانتظار
        _user_states.pop(config.OWNER_ID, None)

        text_input = message.text.strip()

        # التحقق من المدخل (رقم أو يوزر)
        text_input = text_input.replace("@", "").strip()
        try:
            if text_input.isdigit():
                target_id = int(text_input)
            else:
                user = await userbot.get_entity(text_input)
                target_id = user.id
        except Exception as e:
            logger.error(f"Error resolving username {text_input}: {e}")
            await message.reply_text(
                "❌ المدخل غير صالح أو لم يتم العثور على المستخدم.\n"
                "تأكد من إدخال الآيدي (رقم) أو اليوزر بشكل صحيح.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔙 القائمة الرئيسية", callback_data="back_to_start"
                    )]
                ]),
            )
            return

        # إضافة للقائمة البيضاء
        added = data_manager.add_whitelist(target_id)

        # إذا كان مكتوم في الخاص → أزله تلقائياً
        extra = ""
        if data_manager.is_dm_muted(target_id):
            data_manager.remove_dm_mute(target_id)
            extra = "\n🔊 وتم إلغاء كتمه في الخاص تلقائياً"

        if added:
            name = await get_user_name(bot_instance, target_id)
            reply_text = (
                f"✅ تم إضافة {name} ({target_id}) للقائمة البيضاء{extra}"
            )
            logger.info(f"تم إضافة {target_id} للقائمة البيضاء عبر البوت")
        else:
            reply_text = (
                f"⚠️ المستخدم {target_id} موجود مسبقاً في القائمة البيضاء"
            )

        await message.reply_text(
            reply_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 القائمة الرئيسية", callback_data="back_to_start"
                )]
            ]),
        )

    elif state == "waiting_manual_dm_mute":
        # إزالة حالة الانتظار
        _user_states.pop(config.OWNER_ID, None)

        text_input = message.text.strip()

        # التحقق من المدخل (رقم أو يوزر)
        text_input = text_input.replace("@", "").strip()
        try:
            if text_input.isdigit():
                target_id = int(text_input)
            else:
                user = await userbot.get_entity(text_input)
                target_id = user.id
        except Exception as e:
            logger.error(f"Error resolving username {text_input}: {e}")
            await message.reply_text(
                "❌ المدخل غير صالح أو لم يتم العثور على المستخدم.\n"
                "تأكد من إدخال الآيدي (رقم) أو اليوزر بشكل صحيح.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔙 كتم الخاص", callback_data="manual_dm_mute_menu"
                    )]
                ]),
            )
            return

        # لا يمكن كتم نفسك
        if target_id == config.OWNER_ID:
            await message.reply_text(
                "⚠️ لا يمكنك كتم نفسك!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        "🔙 كتم الخاص", callback_data="manual_dm_mute_menu"
                    )]
                ]),
            )
            return

        # إضافة لقائمة الكتم اليدوي في الخاص
        added = data_manager.add_dm_mute_manual(target_id)

        if added:
            name = await get_user_name(bot_instance, target_id)
            reply_text = (
                f"✅ تم كتم {name} ({target_id}) في الخاص\n"
                f"🔇 سيتم حذف جميع رسائله الجديدة تلقائياً"
            )
            logger.info(f"تم كتم يدوي {target_id} في الخاص عبر البوت")
        else:
            reply_text = (
                f"⚠️ المستخدم {target_id} مكتوم مسبقاً في الخاص"
            )

        await message.reply_text(
            reply_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🔙 كتم الخاص", callback_data="manual_dm_mute_menu"
                )]
            ]),
        )

    else:
        # لا يوجد حالة انتظار → وجّه للقائمة
        await message.reply_text("🤖 أرسل /start لعرض القائمة الرئيسية.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# معالج رسائل غير المالك (Catch-all)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


async def non_owner_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رد على أي شخص غير المالك بأن البوت خاص"""
    if update.effective_user and update.effective_user.id != config.OWNER_ID:
        await update.message.reply_text("⛔ هذا البوت خاص ولا يمكنك استخدامه.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# دوال التشغيل والإيقاف
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _build_application() -> Application:
    """بناء Application مع تسجيل جميع المعالجات"""
    application = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .build()
    )

    # تسجيل معالج /start
    application.add_handler(CommandHandler("start", start_handler))

    # تسجيل معالج الأزرار
    application.add_handler(CallbackQueryHandler(handle_callback))

    # تسجيل معالج النصوص (للقائمة البيضاء)
    application.add_handler(
        MessageHandler(
            filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
            handle_text_input,
        )
    )

    # معالج غير المالك (Catch-all) - يجب أن يكون آخر معالج
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & ~filters.COMMAND,
            non_owner_handler,
        )
    )

    return application


async def start_bot() -> None:
    """
    تشغيل الـ Bot مع HTTP Long Polling
    يستخدم python-telegram-bot بدلاً من pyrofork MTProto
    """
    global app

    try:
        app = _build_application()

        # تهيئة التطبيق
        await app.initialize()
        await app.start()

        # بدء الاستقصاء عبر HTTP (الطريقة الموثوقة لاستقبال التحديثات)
        await app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        )

        me = await app.bot.get_me()
        logger.info(f"✅ تم تشغيل الـ Bot: @{me.username} [{me.id}]")
        print(f"✅ تم تشغيل الـ Bot: @{me.username}")

        # ─── فحص ذاتي: إرسال رسالة تأكيد للمالك ───
        try:
            await app.bot.send_message(
                config.OWNER_ID,
                "🟢 البوت يعمل الآن!\n"
                "أرسل /start لعرض لوحة التحكم."
            )
            logger.info("✅ تم إرسال رسالة التأكيد للمالك بنجاح")
        except Exception as e:
            logger.warning(f"⚠️ لم يتمكن من إرسال رسالة التأكيد: {e}")

    except Exception as e:
        logger.critical(f"❌ فشل تشغيل الـ Bot: {e}")
        raise


async def stop_bot() -> None:
    """إيقاف الـ Bot بشكل آمن"""
    global app

    try:
        if app:
            if app.updater and app.updater.running:
                await app.updater.stop()
            if app.running:
                await app.stop()
            await app.shutdown()
            logger.info("تم إيقاف الـ Bot بنجاح")
    except Exception as e:
        logger.error(f"خطأ أثناء إيقاف الـ Bot: {e}")
