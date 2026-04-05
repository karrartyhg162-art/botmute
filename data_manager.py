# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# وحدة إدارة البيانات - مشتركة بين الـ Userbot والـ Bot
# مسؤولة عن قراءة وكتابة بيانات الكتم في ملف data.json
# تستخدم threading.Lock لمنع تعارض الكتابة المتزامنة
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

import json
import os
import logging
import threading
from typing import Dict, List

from config import DATA_FILE

# إعداد نظام التسجيل (logging)
logger = logging.getLogger(__name__)

# قفل لمنع تعارض الكتابة بين الـ Bot والـ Userbot
_lock = threading.RLock()

# الهيكل الافتراضي لملف البيانات
_DEFAULT_DATA: Dict = {
    "dm_muted": [],       # قائمة المكتومين في الخاص (أرقام آيدي) - تلقائي
    "dm_mute_manual": [], # قائمة المكتومين يدوياً في الخاص (حذف رسائلهم فقط)
    "group_muted": {},    # قاموس المكتومين في المجموعات {group_id: [user_ids]}
    "whitelist": []       # قائمة المستثنين من الكتم التلقائي
}


def load_data() -> dict:
    """
    تحميل البيانات من ملف data.json

    - إذا الملف غير موجود → يُنشأ بالهيكل الافتراضي
    - إذا الملف فيه خطأ JSON → يُعاد إنشاؤه بالهيكل الافتراضي
    - يُرجع dict يحتوي على بيانات الكتم
    """
    with _lock:
        try:
            # التحقق من وجود الملف
            if not os.path.exists(DATA_FILE):
                logger.info("ملف البيانات غير موجود، جاري إنشاؤه بالهيكل الافتراضي...")
                _write_default_data()
                return _DEFAULT_DATA.copy()

            # قراءة الملف
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # التحقق من صحة الهيكل
            if not isinstance(data, dict):
                logger.warning("هيكل البيانات غير صالح، جاري إعادة الإنشاء...")
                _write_default_data()
                return _DEFAULT_DATA.copy()

            # التأكد من وجود المفاتيح الأساسية
            if "dm_muted" not in data:
                data["dm_muted"] = []
            if "dm_mute_manual" not in data:
                data["dm_mute_manual"] = []
            if "group_muted" not in data:
                data["group_muted"] = {}
            if "whitelist" not in data:
                data["whitelist"] = []

            return data

        except json.JSONDecodeError:
            logger.error("خطأ في تنسيق JSON، جاري إعادة إنشاء الملف بالهيكل الافتراضي...")
            _write_default_data()
            return _DEFAULT_DATA.copy()

        except Exception as e:
            logger.error(f"خطأ غير متوقع أثناء تحميل البيانات: {e}")
            return _DEFAULT_DATA.copy()


def save_data(data: dict) -> None:
    """
    حفظ البيانات في ملف data.json

    - يستخدم ensure_ascii=False لدعم النصوص العربية
    - يستخدم indent=2 لتنسيق مقروء
    - يستخدم قفل (Lock) لتجنب التعارض بين الـ Bot والـ Userbot
    """
    with _lock:
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("تم حفظ البيانات بنجاح")

        except Exception as e:
            logger.error(f"خطأ أثناء حفظ البيانات: {e}")


def _write_default_data() -> None:
    """
    كتابة الهيكل الافتراضي في ملف البيانات
    ⚠️ هذه دالة داخلية - يجب استدعاؤها داخل القفل فقط
    """
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT_DATA, f, ensure_ascii=False, indent=2)
        logger.info("تم إنشاء ملف البيانات بالهيكل الافتراضي")
    except Exception as e:
        logger.error(f"خطأ أثناء إنشاء ملف البيانات الافتراضي: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# دوال إدارة كتم الخاص (DM Mute)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def add_dm_mute(user_id: int) -> bool:
    """
    إضافة مستخدم لقائمة كتم الخاص

    :param user_id: آيدي المستخدم المراد كتمه
    :return: True إذا تمت الإضافة، False إذا كان موجوداً مسبقاً
    """
    try:
        data = load_data()

        if user_id in data["dm_muted"]:
            logger.debug(f"المستخدم {user_id} موجود مسبقاً في قائمة كتم الخاص")
            return False

        data["dm_muted"].append(user_id)
        save_data(data)
        logger.info(f"تمت إضافة المستخدم {user_id} لقائمة كتم الخاص")
        return True

    except Exception as e:
        logger.error(f"خطأ أثناء إضافة {user_id} لكتم الخاص: {e}")
        return False


def remove_dm_mute(user_id: int) -> bool:
    """
    إزالة مستخدم من قائمة كتم الخاص

    :param user_id: آيدي المستخدم المراد إزالته
    :return: True إذا تمت الإزالة، False إذا لم يكن موجوداً
    """
    try:
        data = load_data()

        if user_id not in data["dm_muted"]:
            logger.debug(f"المستخدم {user_id} غير موجود في قائمة كتم الخاص")
            return False

        data["dm_muted"].remove(user_id)
        save_data(data)
        logger.info(f"تمت إزالة المستخدم {user_id} من قائمة كتم الخاص")
        return True

    except Exception as e:
        logger.error(f"خطأ أثناء إزالة {user_id} من كتم الخاص: {e}")
        return False


def get_dm_muted() -> List[int]:
    """
    الحصول على قائمة المكتومين في الخاص

    :return: قائمة بآيديات المستخدمين المكتومين
    """
    try:
        data = load_data()
        return data.get("dm_muted", [])
    except Exception as e:
        logger.error(f"خطأ أثناء جلب قائمة كتم الخاص: {e}")
        return []


def is_dm_muted(user_id: int) -> bool:
    """
    التحقق إذا المستخدم مكتوم في الخاص

    :param user_id: آيدي المستخدم
    :return: True إذا كان مكتوماً، False إذا لم يكن
    """
    try:
        data = load_data()
        return user_id in data.get("dm_muted", [])
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من كتم {user_id} في الخاص: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# دوال إدارة كتم الخاص اليدوي (Manual DM Mute)
# هذه القائمة للمستخدمين الذين يُضافون يدوياً عبر لوحة التحكم
# رسائلهم تُحذف تلقائياً وتبقى فقط رسائل المالك
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def add_dm_mute_manual(user_id: int) -> bool:
    """
    إضافة مستخدم لقائمة كتم الخاص اليدوي

    :param user_id: آيدي المستخدم المراد كتمه
    :return: True إذا تمت الإضافة، False إذا كان موجوداً مسبقاً
    """
    try:
        data = load_data()

        if user_id in data["dm_mute_manual"]:
            logger.debug(f"المستخدم {user_id} موجود مسبقاً في قائمة كتم الخاص اليدوي")
            return False

        data["dm_mute_manual"].append(user_id)
        save_data(data)
        logger.info(f"تمت إضافة المستخدم {user_id} لقائمة كتم الخاص اليدوي")
        return True

    except Exception as e:
        logger.error(f"خطأ أثناء إضافة {user_id} لكتم الخاص اليدوي: {e}")
        return False


def remove_dm_mute_manual(user_id: int) -> bool:
    """
    إزالة مستخدم من قائمة كتم الخاص اليدوي

    :param user_id: آيدي المستخدم المراد إزالته
    :return: True إذا تمت الإزالة، False إذا لم يكن موجوداً
    """
    try:
        data = load_data()

        if user_id not in data["dm_mute_manual"]:
            logger.debug(f"المستخدم {user_id} غير موجود في قائمة كتم الخاص اليدوي")
            return False

        data["dm_mute_manual"].remove(user_id)
        save_data(data)
        logger.info(f"تمت إزالة المستخدم {user_id} من قائمة كتم الخاص اليدوي")
        return True

    except Exception as e:
        logger.error(f"خطأ أثناء إزالة {user_id} من كتم الخاص اليدوي: {e}")
        return False


def get_dm_mute_manual() -> List[int]:
    """
    الحصول على قائمة المكتومين يدوياً في الخاص

    :return: قائمة بآيديات المستخدمين المكتومين يدوياً
    """
    try:
        data = load_data()
        return data.get("dm_mute_manual", [])
    except Exception as e:
        logger.error(f"خطأ أثناء جلب قائمة كتم الخاص اليدوي: {e}")
        return []


def is_dm_muted_manual(user_id: int) -> bool:
    """
    التحقق إذا المستخدم مكتوم يدوياً في الخاص

    :param user_id: آيدي المستخدم
    :return: True إذا كان مكتوماً يدوياً، False إذا لم يكن
    """
    try:
        data = load_data()
        return user_id in data.get("dm_mute_manual", [])
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من كتم {user_id} في الخاص اليدوي: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# دوال إدارة كتم المجموعات (Group Mute)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def add_group_mute(group_id: int, user_id: int) -> bool:
    """
    إضافة مستخدم لقائمة كتم مجموعة معينة

    :param group_id: آيدي المجموعة (يُخزن كـ string في JSON)
    :param user_id: آيدي المستخدم المراد كتمه
    :return: True إذا تمت الإضافة، False إذا كان موجوداً مسبقاً
    """
    try:
        data = load_data()
        group_key = str(group_id)

        # إنشاء قائمة للمجموعة إذا لم تكن موجودة
        if group_key not in data["group_muted"]:
            data["group_muted"][group_key] = []

        if user_id in data["group_muted"][group_key]:
            logger.debug(f"المستخدم {user_id} مكتوم مسبقاً في المجموعة {group_id}")
            return False

        data["group_muted"][group_key].append(user_id)
        save_data(data)
        logger.info(f"تمت إضافة المستخدم {user_id} لكتم المجموعة {group_id}")
        return True

    except Exception as e:
        logger.error(f"خطأ أثناء إضافة {user_id} لكتم المجموعة {group_id}: {e}")
        return False


def remove_group_mute(group_id: int, user_id: int) -> bool:
    """
    إزالة مستخدم من قائمة كتم مجموعة معينة

    :param group_id: آيدي المجموعة
    :param user_id: آيدي المستخدم المراد إزالته
    :return: True إذا تمت الإزالة، False إذا لم يكن موجوداً
    """
    try:
        data = load_data()
        group_key = str(group_id)

        if group_key not in data["group_muted"]:
            logger.debug(f"المجموعة {group_id} غير موجودة في بيانات الكتم")
            return False

        if user_id not in data["group_muted"][group_key]:
            logger.debug(f"المستخدم {user_id} غير مكتوم في المجموعة {group_id}")
            return False

        data["group_muted"][group_key].remove(user_id)

        # حذف المجموعة إذا أصبحت فارغة
        if not data["group_muted"][group_key]:
            del data["group_muted"][group_key]
            logger.debug(f"تم حذف المجموعة {group_id} لأنها أصبحت فارغة")

        save_data(data)
        logger.info(f"تمت إزالة المستخدم {user_id} من كتم المجموعة {group_id}")
        return True

    except Exception as e:
        logger.error(f"خطأ أثناء إزالة {user_id} من كتم المجموعة {group_id}: {e}")
        return False


def get_group_muted(group_id: int) -> List[int]:
    """
    الحصول على قائمة المكتومين في مجموعة معينة

    :param group_id: آيدي المجموعة
    :return: قائمة بآيديات المستخدمين المكتومين في هذه المجموعة
    """
    try:
        data = load_data()
        group_key = str(group_id)
        return data.get("group_muted", {}).get(group_key, [])
    except Exception as e:
        logger.error(f"خطأ أثناء جلب مكتومين المجموعة {group_id}: {e}")
        return []


def is_group_muted(group_id: int, user_id: int) -> bool:
    """
    التحقق إذا المستخدم مكتوم في مجموعة معينة

    :param group_id: آيدي المجموعة
    :param user_id: آيدي المستخدم
    :return: True إذا كان مكتوماً، False إذا لم يكن
    """
    try:
        data = load_data()
        group_key = str(group_id)
        return user_id in data.get("group_muted", {}).get(group_key, [])
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من كتم {user_id} في المجموعة {group_id}: {e}")
        return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# دوال إدارة القائمة البيضاء (Whitelist)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def add_whitelist(user_id: int) -> bool:
    """
    إضافة مستخدم للقائمة البيضاء

    :param user_id: آيدي المستخدم
    :return: True إذا تمت الإضافة، False إذا كان موجوداً مسبقاً
    """
    try:
        data = load_data()
        if user_id in data["whitelist"]:
            logger.debug(f"المستخدم {user_id} موجود مسبقاً في القائمة البيضاء")
            return False
        data["whitelist"].append(user_id)
        save_data(data)
        logger.info(f"تمت إضافة المستخدم {user_id} للقائمة البيضاء")
        return True
    except Exception as e:
        logger.error(f"خطأ أثناء إضافة {user_id} للقائمة البيضاء: {e}")
        return False


def remove_whitelist(user_id: int) -> bool:
    """
    إزالة مستخدم من القائمة البيضاء

    :param user_id: آيدي المستخدم
    :return: True إذا تمت الإزالة، False إذا لم يكن موجوداً
    """
    try:
        data = load_data()
        if user_id not in data["whitelist"]:
            logger.debug(f"المستخدم {user_id} غير موجود في القائمة البيضاء")
            return False
        data["whitelist"].remove(user_id)
        save_data(data)
        logger.info(f"تمت إزالة المستخدم {user_id} من القائمة البيضاء")
        return True
    except Exception as e:
        logger.error(f"خطأ أثناء إزالة {user_id} من القائمة البيضاء: {e}")
        return False


def get_whitelist() -> List[int]:
    """
    الحصول على القائمة البيضاء

    :return: قائمة بآيديات المستخدمين المستثنين
    """
    try:
        data = load_data()
        return data.get("whitelist", [])
    except Exception as e:
        logger.error(f"خطأ أثناء جلب القائمة البيضاء: {e}")
        return []


def is_whitelisted(user_id: int) -> bool:
    """
    التحقق إذا المستخدم في القائمة البيضاء

    :param user_id: آيدي المستخدم
    :return: True إذا كان مستثنى، False إذا لم يكن
    """
    try:
        data = load_data()
        return user_id in data.get("whitelist", [])
    except Exception as e:
        logger.error(f"خطأ أثناء التحقق من {user_id} في القائمة البيضاء: {e}")
        return False
