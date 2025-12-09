"""
Additional.py - Qo'shimcha funksiyalar moduli
/add buyrug'i orqali ALL DATA Google Sheet sozlash
Barcha hisobotlar (Toshkent va viloyat) bitta "ALL DATA" sheetga saqlanadi
"""

import logging
import re
import json
import os
from datetime import datetime
from typing import Optional, List, Dict

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ParseMode

from config import ADMIN_ID, HELPER_ID

# Router yaratish
additional_router = Router()

# ==================== STATES ====================

class AdditionalStates(StatesGroup):
    """Qo'shimcha funksiyalar uchun holatlar"""
    waiting_for_all_data_sheet_url = State()


# ==================== CONFIG FILE ====================

ALL_DATA_CONFIG_FILE = "all_data_config.json"


# ==================== HELPER FUNCTIONS ====================

def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin ekanligini tekshirish"""
    return user_id == ADMIN_ID or user_id == HELPER_ID


def extract_spreadsheet_id(url: str) -> Optional[str]:
    """Google Sheets URL dan spreadsheet ID ni olish"""
    patterns = [
        r'/spreadsheets/d/([a-zA-Z0-9-_]+)',
        r'spreadsheets/d/([a-zA-Z0-9-_]+)',
        r'^([a-zA-Z0-9-_]+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def load_all_data_config() -> Dict:
    """ALL DATA config faylini yuklash"""
    try:
        if os.path.exists(ALL_DATA_CONFIG_FILE):
            with open(ALL_DATA_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"❌ Config yuklashda xato: {e}")
    return {}


def save_all_data_config(config: Dict) -> bool:
    """ALL DATA config faylini saqlash"""
    try:
        with open(ALL_DATA_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logging.error(f"❌ Config saqlashda xato: {e}")
        return False


def get_all_data_spreadsheet_id() -> Optional[str]:
    """ALL DATA spreadsheet ID ni olish"""
    config = load_all_data_config()
    return config.get('spreadsheet_id')


def set_all_data_spreadsheet_id(spreadsheet_id: str) -> bool:
    """ALL DATA spreadsheet ID ni o'rnatish"""
    config = load_all_data_config()
    config['spreadsheet_id'] = spreadsheet_id
    config['updated_at'] = datetime.now().strftime('%d.%m.%Y %H:%M')
    return save_all_data_config(config)


# ==================== KEYBOARDS ====================

def get_all_data_menu_keyboard() -> InlineKeyboardMarkup:
    """ALL DATA boshqaruvi menyusi"""
    buttons = [
        [InlineKeyboardButton(text="📊 Google Sheet sozlash", callback_data="alldata_set_sheet")],
        [InlineKeyboardButton(text="ℹ️ Joriy sozlamalar", callback_data="alldata_current_settings")],
        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="alldata_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Bekor qilish tugmasi"""
    buttons = [
        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="alldata_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== HANDLERS ====================

@additional_router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext):
    """
    /add buyrug'i - ALL DATA Google Sheet sozlash
    Barcha hisobotlar shu sheetga saqlanadi
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun!")
        return
    
    # Joriy sozlamalarni ko'rsatish
    current_id = get_all_data_spreadsheet_id()
    status_text = ""
    
    if current_id:
        status_text = f"\n\n📋 Joriy Sheet ID:\n`{current_id}`"
    else:
        status_text = "\n\n⚠️ Hozircha Sheet sozlanmagan"
    
    await message.answer(
        f"📊 **ALL DATA Sheet Boshqaruvi**\n\n"
        f"Bu yerda barcha hisobotlar saqlanadigan Google Sheet ni sozlashingiz mumkin.\n"
        f"Barcha topshirilgan hisobotlar (Toshkent va viloyat) shu sheetga saqlanadi."
        f"{status_text}",
        reply_markup=get_all_data_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )


@additional_router.callback_query(F.data == "alldata_set_sheet")
async def alldata_set_sheet(callback_query: CallbackQuery, state: FSMContext):
    """Google Sheet URL so'rash"""
    user_id = callback_query.from_user.id
    
    if not is_admin(user_id):
        await callback_query.answer("⛔ Bu funksiya faqat adminlar uchun!", show_alert=True)
        return
    
    await callback_query.message.edit_text(
        "📊 **Google Sheets URL kiriting**\n\n"
        "Google Sheets havolasini yuboring.\n"
        "Misol: `https://docs.google.com/spreadsheets/d/ABC123.../edit`\n\n"
        "⚠️ Sheet service account bilan ulashilgan bo'lishi kerak!",
        reply_markup=get_cancel_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    await state.set_state(AdditionalStates.waiting_for_all_data_sheet_url)
    await callback_query.answer()


@additional_router.message(AdditionalStates.waiting_for_all_data_sheet_url)
async def process_all_data_sheet_url(message: Message, state: FSMContext):
    """Google Sheet URL ni qayta ishlash"""
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Bu funksiya faqat adminlar uchun!")
        await state.clear()
        return
    
    url = message.text.strip()
    spreadsheet_id = extract_spreadsheet_id(url)
    
    if not spreadsheet_id:
        await message.answer(
            "❌ **Noto'g'ri URL format!**\n\n"
            "To'g'ri Google Sheets havolasini yuboring.\n"
            "Misol: `https://docs.google.com/spreadsheets/d/ABC123.../edit`",
            reply_markup=get_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Sheetga ulanishni tekshirish
    from google_sheets_integration import test_all_data_sheet_connection
    
    success, sheet_title = test_all_data_sheet_connection(spreadsheet_id)
    
    if success:
        # Config ga saqlash
        if set_all_data_spreadsheet_id(spreadsheet_id):
            await message.answer(
                f"✅ **Google Sheet muvaffaqiyatli sozlandi!**\n\n"
                f"📋 Sheet nomi: `{sheet_title}`\n"
                f"🆔 Sheet ID: `{spreadsheet_id}`\n\n"
                f"Endi barcha hisobotlar \"ALL DATA\" listiga saqlanadi.",
                parse_mode=ParseMode.MARKDOWN
            )
            logging.info(f"✅ ALL DATA Sheet sozlandi: {spreadsheet_id} by admin {user_id}")
        else:
            await message.answer(
                "❌ Config faylga saqlashda xato yuz berdi!\n"
                "Qaytadan urinib ko'ring.",
                reply_markup=get_cancel_keyboard()
            )
    else:
        await message.answer(
            f"❌ **Sheetga ulanishda xato!**\n\n"
            f"Sabab: {sheet_title}\n\n"
            f"Tekshiring:\n"
            f"1. Sheet URL to'g'ri kiritilganmi\n"
            f"2. Sheet service account bilan ulashilganmi\n"
            f"3. Service account'ga 'Editor' huquqi berilganmi",
            reply_markup=get_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    await state.clear()


@additional_router.callback_query(F.data == "alldata_current_settings")
async def alldata_current_settings(callback_query: CallbackQuery):
    """Joriy sozlamalarni ko'rsatish"""
    user_id = callback_query.from_user.id
    
    if not is_admin(user_id):
        await callback_query.answer("⛔ Bu funksiya faqat adminlar uchun!", show_alert=True)
        return
    
    current_id = get_all_data_spreadsheet_id()
    config = load_all_data_config()
    
    if current_id:
        updated_at = config.get('updated_at', 'Noma\'lum')
        await callback_query.message.edit_text(
            f"📊 **Joriy ALL DATA sozlamalari**\n\n"
            f"🆔 Spreadsheet ID:\n`{current_id}`\n\n"
            f"🔗 Link:\n`https://docs.google.com/spreadsheets/d/{current_id}`\n\n"
            f"📅 O'zgartirilgan: {updated_at}",
            reply_markup=get_all_data_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await callback_query.message.edit_text(
            "⚠️ **ALL DATA Sheet sozlanmagan!**\n\n"
            "Iltimos, avval Google Sheet ni sozlang.",
            reply_markup=get_all_data_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    await callback_query.answer()


@additional_router.callback_query(F.data == "alldata_cancel")
async def alldata_cancel(callback_query: CallbackQuery, state: FSMContext):
    """Bekor qilish"""
    await state.clear()
    
    try:
        await callback_query.message.delete()
    except:
        await callback_query.message.edit_text("❌ Bekor qilindi.")
    
    await callback_query.answer("Bekor qilindi")


# ==================== QUICK COMMANDS ====================

@additional_router.message(Command("alldata"))
async def cmd_alldata_status(message: Message):
    """
    /alldata - ALL DATA sheet holatini ko'rish
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun!")
        return
    
    current_id = get_all_data_spreadsheet_id()
    
    if current_id:
        from google_sheets_integration import get_all_data_stats
        stats = get_all_data_stats(current_id)
        
        await message.answer(
            f"📊 **ALL DATA Sheet holati**\n\n"
            f"🆔 Sheet ID: `{current_id[:20]}...`\n"
            f"📋 Jami hisobotlar: {stats.get('total', 0)}\n"
            f"🏙️ Toshkent: {stats.get('tashkent', 0)}\n"
            f"📍 Viloyatlar: {stats.get('regions', 0)}\n\n"
            f"🔗 [Sheet ni ochish](https://docs.google.com/spreadsheets/d/{current_id})",
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    else:
        await message.answer(
            "⚠️ ALL DATA Sheet sozlanmagan!\n\n"
            "/add buyrug'i orqali sozlang."
        )


@additional_router.message(Command("resetalldata"))
async def cmd_reset_alldata(message: Message):
    """
    /resetalldata - ALL DATA sozlamalarini tozalash
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("⛔ Bu buyruq faqat adminlar uchun!")
        return
    
    if os.path.exists(ALL_DATA_CONFIG_FILE):
        os.remove(ALL_DATA_CONFIG_FILE)
        await message.answer("✅ ALL DATA sozlamalari tozalandi!")
        logging.info(f"🗑️ ALL DATA config tozalandi by admin {user_id}")
    else:
        await message.answer("ℹ️ Sozlamalar allaqachon bo'sh.")
