import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any

from aiogram import Router, F, Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton

from config import ADMIN_ID, HELPER_ID
from database import (
    add_sales_report, get_user_assigned_group, update_report_status_in_db,
    check_user_blocked, get_user_by_telegram_id, get_group_google_sheet,
    get_user_reports_count, get_reports_by_user, get_all_users
)
from keyboards import (
    get_cancel_report_inline_keyboard, get_main_menu_reply_keyboard,
    get_report_confirmation_keyboard, get_report_confirmed_keyboard,
    get_group_report_keyboard, get_edit_selection_keyboard,
    get_rejection_reason_keyboard, get_contact_helper_keyboard,
    get_yes_no_additional_phone_inline_keyboard, get_region_selection_keyboard
)
from google_sheets_integration import save_report_to_sheets, is_tashkent_region, get_daily_worksheet_name, save_report_to_all_data, get_daily_all_data_worksheet_name
from additional import get_all_data_spreadsheet_id

# Router yaratish
otchot_router = Router()


# ==================== FSM HOLATLARI ====================

class ReportState(StatesGroup):
    waiting_for_region_selection = State()
    waiting_for_template_data = State()
    waiting_for_product_image = State()
    waiting_for_confirmation = State()
    waiting_for_edit_selection = State()


# ==================== KONSTANTALAR ====================

# YANGILANGAN TEMPLATE - Dastavka izohdan oldin
REPORT_CAPTION_TEMPLATE = """📝 Yangi Hisobot:

👤 Mijoz: {client_name}

📱 Telefon: {phone_number}
{additional_phone_line}
🛍️ Mahsulot: {product_type}

📍 Manzil: {client_location}

🆔 Shartnoma raqami: {contract_id}

💰 Shartnoma summasi: {contract_amount}

🚛 Dastavka: {delivery}

📝 Izoh: {note}

👫 Sotuvchi: {seller_name}

{region_type_line}

{status_line}"""


# ==================== YORDAMCHI FUNKSIYALAR ====================

def format_amount(amount_str: str) -> str:
    """Summani formatlash funksiyasi"""
    if not amount_str:
        return amount_str
    
    clean_amount = re.sub(r'[^\d]', '', str(amount_str))
    
    if not clean_amount:
        return amount_str
    
    formatted = ""
    for i, digit in enumerate(reversed(clean_amount)):
        if i > 0 and i % 3 == 0:
            formatted = "." + formatted
        formatted = digit + formatted
    
    return formatted


def format_phone_number(phone: str) -> str:
    """
    Telefon raqamini qanday kiritilgan bo'lsa shundayligicha qaytarish
    Hech qanday formatlash qilinmaydi
    """
    if not phone:
        return phone
    return phone.strip()


def validate_phone_number(phone: str) -> bool:
    """Telefon raqamini validatsiya qilish"""
    if not phone:
        return False
    digits_only = re.sub(r'[^\d]', '', phone)
    return len(digits_only) >= 9


def validate_text_field(text: str, min_length: int = 2) -> bool:
    """Matn maydonlarini validatsiya qilish"""
    return bool(text and text.strip() and len(text.strip()) >= min_length)


def parse_template_data(text: str) -> Optional[Dict[str, str]]:
    """
    Template ma'lumotlarini parse qilish
    YANGILANGAN: Dastavka maydoni qo'shildi
    """
    try:
        data = {}
        lines = text.strip().split('\n')
        
        field_mapping = {
            '👤 Mijoz:': 'client_name',
            '📞 Asosiy raqam:': 'phone_number',
            '📞 Qo\'shimcha raqam:': 'additional_phone_number',
            '📦 Mahsulot:': 'product_type',
            '📍 Manzil:': 'client_location',
            '💵 Narx:': 'contract_amount',
            '🆔 Shartnoma raqami:': 'contract_id',
            '🚛 Dastavka:': 'delivery',  # YANGI MAYDON
            '📝 Izoh:': 'note',
            '👫 Sotuvchi:': 'seller_name'
        }
        
        for line in lines:
            line = line.strip()
            for key, field_name in field_mapping.items():
                if line.startswith(key):
                    value = line.split(':', 1)[1].strip() if ':' in line else ''
                    if value:
                        data[field_name] = value
                    break
        
        # Majburiy maydonlar
        required_fields = ['client_name', 'phone_number', 'product_type', 'client_location', 'contract_id', 'contract_amount', 'seller_name']
        for field in required_fields:
            if field not in data or not data[field]:
                return None
        
        # Telefon raqamlarni formatlash
        if 'phone_number' in data:
            data['phone_number'] = format_phone_number(data['phone_number'])
        if 'additional_phone_number' in data:
            data['additional_phone_number'] = format_phone_number(data['additional_phone_number'])
        
        # Default qiymatlar
        if 'delivery' not in data:
            data['delivery'] = 'Belgilanmagan'
        if 'note' not in data:
            data['note'] = 'Yo\'q'
        
        return data
    except Exception as e:
        logging.error(f"Template parse qilishda xatolik: {e}")
        return None


def get_seller_contact_keyboard(seller_telegram_id: int) -> InlineKeyboardMarkup:
    """Sotuvchi bilan bog'lanish klaviaturasi"""
    buttons = [
        [
            InlineKeyboardButton(
                text="💬 Sotuvchi bilan bog'lanish",
                url=f"tg://user?id={seller_telegram_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Orqaga",
                callback_data="back_to_group_report"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def get_seller_detailed_profile(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Sotuvchi batafsil profil ma'lumotlarini olish"""
    try:
        user_info = await get_user_by_telegram_id(telegram_id)
        if not user_info:
            return None
        
        user_id, telegram_id, full_name, reg_date, is_blocked, group_name = user_info
        
        total_reports = await get_user_reports_count(telegram_id)
        recent_reports = await get_reports_by_user(telegram_id, 10)
        
        confirmed_count = 0
        pending_count = 0
        rejected_count = 0
        
        for report in recent_reports:
            status = report[12]
            if status == "confirmed":
                confirmed_count += 1
            elif status == "pending":
                pending_count += 1
            elif status == "rejected":
                rejected_count += 1
        
        reg_date_formatted = "Noma'lum"
        if reg_date:
            try:
                if " " in reg_date:
                    reg_date_formatted = reg_date.split(' ')[0]
                else:
                    reg_date_formatted = reg_date
            except:
                reg_date_formatted = reg_date
        
        last_activity = "Hech qachon"
        if recent_reports:
            try:
                last_report = recent_reports[0]
                last_submission = last_report[11]
                if last_submission:
                    if isinstance(last_submission, str):
                        last_activity = last_submission.split(' ')[0] if ' ' in last_submission else last_submission
                    else:
                        last_activity = str(last_submission)[:10]
            except:
                last_activity = "Noma'lum"
        
        return {
            'telegram_id': telegram_id,
            'full_name': full_name,
            'group_name': group_name,
            'reg_date': reg_date_formatted,
            'is_blocked': is_blocked,
            'total_reports': total_reports,
            'confirmed_count': confirmed_count,
            'pending_count': pending_count,
            'rejected_count': rejected_count,
            'recent_reports': recent_reports[:5],
            'last_activity': last_activity
        }
    
    except Exception as e:
        logging.error(f"Sotuvchi batafsil profil ma'lumotlarini olishda xatolik: {e}")
        return None


def format_seller_profile_message(profile_data: Dict[str, Any]) -> str:
    """Sotuvchi profil xabarini formatlash"""
    if not profile_data:
        return "❌ Sotuvchi ma'lumotlari topilmadi."
    
    status_text = "🔒 BLOKLANGAN" if profile_data['is_blocked'] else "✅ FAOL"
    status_color = "🔴" if profile_data['is_blocked'] else "🟢"
    
    total = profile_data['total_reports']
    confirmed = profile_data['confirmed_count']
    pending = profile_data['pending_count']
    rejected = profile_data['rejected_count']
    
    success_rate = 0
    if total > 0:
        success_rate = round((confirmed / total) * 100, 1)
    
    profile_text = f"""👨‍💼 SOTUVCHI PROFILI

{status_color} **ASOSIY MA'LUMOTLAR**
━━━━━━━━━━━━━━━━━━━━━━━
📝 Ism: **{profile_data['full_name']}**
🆔 Telegram ID: `{profile_data['telegram_id']}`
👥 Guruh: **{profile_data['group_name']}**
📅 Ro'yxatdan o'tgan: **{profile_data['reg_date']}**
🔘 Holat: **{status_text}**
📊 So'nggi faollik: **{profile_data['last_activity']}**

📈 **HISOBOTLAR STATISTIKASI**
━━━━━━━━━━━━━━━━━━━━━━━
📋 Jami hisobotlar: **{total} ta**
✅ Tasdiqlangan: **{confirmed} ta**
⏳ Kutilayotgan: **{pending} ta**
❌ Rad etilgan: **{rejected} ta**
🎯 Tasdiqlash foizi: **{success_rate}%**

📋 **SO'NGGI HISOBOTLAR**
━━━━━━━━━━━━━━━━━━━━━━━"""
    
    recent_reports = profile_data.get('recent_reports', [])
    if recent_reports:
        for i, report in enumerate(recent_reports, 1):
            try:
                report_id = report[0]
                client_name = report[2]
                contract_id = report[5]
                product_type = report[7]
                client_location = report[8]
                submission_date = report[10]
                status = report[12]
                is_tashkent = report[17] if len(report) > 17 else 0
                
                if status == "confirmed":
                    status_icon = "✅"
                elif status == "pending":
                    status_icon = "⏳"
                elif status == "rejected":
                    status_icon = "❌"
                else:
                    status_icon = "❓"
                
                product_short = product_type[:30] + "..." if len(product_type) > 30 else product_type
                client_short = client_name[:20] + "..." if len(client_name) > 20 else client_name
                location_icon = "🏙️" if is_tashkent else "📍"
                
                profile_text += f"""
**{i}.** {status_icon} **{product_short}**
   👤 Mijoz: {client_short}
   {location_icon} Hudud: {'Toshkent shahar' if is_tashkent else 'Viloyat'}
   📄 Shartnoma: `{contract_id}`
   📅 Sana: {submission_date}"""
            
            except Exception as e:
                logging.error(f"Hisobot ma'lumotlarini formatlashda xatolik: {e}")
                continue
    else:
        profile_text += "\n❌ Hozircha hisobotlar yo'q"
    
    profile_text += f"""

💡 **QO'SHIMCHA MA'LUMOTLAR**
━━━━━━━━━━━━━━━━━━━━━━━
📞 Sotuvchi bilan to'g'ridan-to'g'ri bog'lanish uchun quyidagi tugmani bosing
🔗 Profil ma'lumotlari real vaqtda yangilanadi
📊 Statistika so'nggi barcha hisobotlar asosida hisoblangan"""
    
    return profile_text


async def find_user_by_name(full_name: str) -> Optional[int]:
    """Ism bo'yicha foydalanuvchi telegram ID'sini topish"""
    try:
        all_users = await get_all_users()
        for user in all_users:
            if user[2] == full_name:
                return user[1]
        return None
    except Exception as e:
        logging.error(f"Foydalanuvchini topishda xatolik: {e}")
        return None


async def delete_previous_messages(bot: Bot, chat_id: int, state: FSMContext):
    """Oldingi bot va foydalanuvchi xabarlarini o'chirish"""
    data = await state.get_data()
    bot_prompt_id = data.get("last_bot_prompt_id")
    user_reply_id = data.get("last_user_reply_id")
    
    if bot_prompt_id:
        try:
            await bot.delete_message(chat_id, bot_prompt_id)
        except (TelegramBadRequest, Exception) as e:
            logging.warning(f"Bot xabarini o'chirishda xatolik {bot_prompt_id}: {e}")
    
    if user_reply_id:
        try:
            await bot.delete_message(chat_id, user_reply_id)
        except (TelegramBadRequest, Exception) as e:
            logging.warning(f"Foydalanuvchi xabarini o'chirishda xatolik {user_reply_id}: {e}")
    
    await state.update_data(last_bot_prompt_id=None, last_user_reply_id=None)


async def process_step(message: Message, state: FSMContext, bot: Bot, next_state: State, prompt_text: str,
                       keyboard_markup=None):
    """Keyingi bosqichga o'tish uchun umumiy funksiya"""
    await state.update_data(last_user_reply_id=message.message_id)
    await delete_previous_messages(bot, message.chat.id, state)
    
    sent_message = await message.answer(
        prompt_text,
        reply_markup=keyboard_markup or get_cancel_report_inline_keyboard()
    )
    
    await state.set_state(next_state)
    await state.update_data(last_bot_prompt_id=sent_message.message_id)


async def show_error_and_retry(message: Message, state: FSMContext, bot: Bot, error_text: str):
    """Xatolik xabarini ko'rsatish va qayta urinish"""
    await state.update_data(last_user_reply_id=message.message_id)
    await delete_previous_messages(bot, message.chat.id, state)
    
    error_prompt = await message.answer(
        error_text,
        reply_markup=get_cancel_report_inline_keyboard()
    )
    await state.update_data(last_bot_prompt_id=error_prompt.message_id)


# ==================== HISOBOT TOPSHIRISH JARAYONI ====================

@otchot_router.message(F.text == "📝 Hisobot topshirish")
async def start_report_submission(message: Message, state: FSMContext, bot: Bot):
    """Hisobot topshirish jarayonini boshlash - viloyat tanlash"""
    user_id = message.from_user.id
    
    if await check_user_blocked(user_id):
        await message.answer(
            "🚫 Sizning hisobingiz vaqtincha bloklangan.\n"
            "Qo'shimcha ma'lumot uchun admin bilan bog'laning."
        )
        return
    
    assigned_group = await get_user_assigned_group(user_id)
    if not assigned_group:
        await message.answer(
            "⚠️ Sizga hali guruh tayinlanmagan.\n"
            "Admin bilan bog'lanib, guruhga qo'shilishingizni so'rang."
        )
        return
    
    await state.clear()
    
    today_date = datetime.now().strftime('%d.%m.%Y')
    
    sent_message = await message.answer(
        f"📍 Iltimos, viloyatni tanlang:\n\n"
        f"🏙️ <b>Toshkent shahar</b> - SH {today_date} sheetga saqlanadi\n"
        f"📍 <b>Viloyatlar</b> - VL {today_date} sheetga saqlanadi\n\n"
        f"💡 Har kuni yangi sheet avtomatik ochiladi!",
        reply_markup=get_region_selection_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.set_state(ReportState.waiting_for_region_selection)
    await state.update_data(last_bot_prompt_id=sent_message.message_id)
    
    logging.info(f"Foydalanuvchi {user_id} hisobot topshirish jarayonini boshladi")


@otchot_router.callback_query(ReportState.waiting_for_region_selection, F.data.startswith("select_region_"))
async def handle_region_selection(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    """Viloyat tanlanganida template yuborish"""
    region = callback_query.data.replace("select_region_", "")
    
    is_tashkent = is_tashkent_region(region)
    
    await state.update_data(selected_region=region, is_tashkent=is_tashkent)
    
    sheet_name = get_daily_worksheet_name(is_tashkent)
    
    region_type = f"🏙️ Toshkent shahar ({sheet_name} sheetga saqlanadi)" if is_tashkent else f"📍 {region} ({sheet_name} sheetga saqlanadi)"
    
    # YANGILANGAN TEMPLATE - Dastavka maydoni qo'shildi
    template_text = f"""👤 Mijoz: 
📞 Asosiy raqam: 
📞 Qo'shimcha raqam: 
📦 Mahsulot: 
📍 Manzil: {region}
💵 Narx: 
🆔 Shartnoma raqami: 
🚛 Dastavka: 
📝 Izoh: 
👫 Sotuvchi: """
    
    await callback_query.message.edit_text(
        f"📋 Quyidagi templateni to'ldiring va qayta yuboring:\n\n"
        f"🗂️ <b>{region_type}</b>\n\n"
        f"⚠️ Diqqat: Har bir maydonni to'ldiring va `:` belgisidan keyin ma'lumotni kiriting.\n\n"
        f"<code>{template_text}</code>\n\n"
        f"💡 Nusxa olish uchun yuqoridagi matnni bosib ushlab turing.",
        reply_markup=get_cancel_report_inline_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    await state.set_state(ReportState.waiting_for_template_data)
    await callback_query.answer()


@otchot_router.message(ReportState.waiting_for_template_data, F.text)
async def process_template_data(message: Message, state: FSMContext, bot: Bot):
    """Template ma'lumotlarini parse qilish va tasdiqlashga o'tkazish"""
    template_text = message.text.strip()
    
    parsed_data = parse_template_data(template_text)
    
    if not parsed_data:
        await show_error_and_retry(
            message, state, bot,
            "⚠️ Ma'lumotlarni to'g'ri formatda kiriting!\n\n"
            "Iltimos, barcha majburiy maydonlarni to'ldiring:\n"
            "• 👤 Mijoz:\n"
            "• 📞 Asosiy raqam:\n"
            "• 📦 Mahsulot:\n"
            "• 📍 Manzil:\n"
            "• 💵 Narx:\n"
            "• 🆔 Shartnoma raqami:\n"
            "• 🚛 Dastavka:\n"
            "• 👫 Sotuvchi:\n\n"
            "Qaytadan kiriting:"
        )
        return
    
    data = await state.get_data()
    selected_region = data.get('selected_region', '')
    is_tashkent = data.get('is_tashkent', False)
    
    if selected_region and selected_region not in parsed_data['client_location']:
        parsed_data['client_location'] = f"{parsed_data['client_location']}, {selected_region}"
    
    parsed_data['contract_amount'] = format_amount(parsed_data['contract_amount'])
    
    await state.update_data(**parsed_data)
    
    await process_step(
        message, state, bot,
        ReportState.waiting_for_product_image,
        "📸 Endi mahsulot rasmini yuboring:\n\n"
        "💡 Rasmni yuqori sifatda yuborish tavsiya etiladi."
    )
    
    logging.info(f"Template ma'lumotlari qabul qilindi va parse qilindi (Toshkent: {is_tashkent})")


@otchot_router.message(ReportState.waiting_for_product_image, F.photo)
async def process_product_image(message: Message, state: FSMContext, bot: Bot):
    """Mahsulot rasmini qayta ishlash va tasdiqlashni ko'rsatish"""
    photo = message.photo[-1]
    photo_id = photo.file_id
    
    await state.update_data(product_image_id=photo_id)
    
    data = await state.get_data()
    
    is_tashkent = data.get('is_tashkent', False)
    sheet_name = get_daily_worksheet_name(is_tashkent)
    region_type_text = f"🏙️ Hudud: Toshkent shahar ({sheet_name})" if is_tashkent else f"📍 Hudud: Viloyat ({sheet_name})"
    
    additional_phone = data.get('additional_phone_number', '')
    additional_phone_line = f"📱 Qo'shimcha: {additional_phone}\n" if additional_phone and additional_phone != 'Mavjud emas' else ""
    
    seller_name = data.get('seller_name', 'Noma\'lum')
    delivery = data.get('delivery', 'Belgilanmagan')
    
    confirmation_text = f"""📝 HISOBOT TASDIQLASH

👤 Mijoz: {data.get('client_name')}

📱 Telefon: {data.get('phone_number')}
{additional_phone_line}🛍️ Mahsulot: {data.get('product_type')}

📍 Manzil: {data.get('client_location')}

🆔 Shartnoma raqami: {data.get('contract_id')}

💰 Shartnoma summasi: {data.get('contract_amount')}

🚛 Dastavka: {delivery}

📝 Izoh: {data.get('note', 'Yo\'q')}

👫 Sotuvchi: {seller_name}

{region_type_text}

Ma'lumotlar to'g'rimi?"""
    
    await delete_previous_messages(bot, message.chat.id, state)
    
    sent_message = await message.answer_photo(
        photo=photo_id,
        caption=confirmation_text,
        reply_markup=get_report_confirmation_keyboard()
    )
    
    await state.set_state(ReportState.waiting_for_confirmation)
    await state.update_data(confirmation_message_id=sent_message.message_id)
    
    logging.info(f"Mahsulot rasmi qabul qilindi va tasdiqlash ko'rsatildi (Toshkent: {is_tashkent})")


@otchot_router.message(ReportState.waiting_for_product_image)
async def handle_invalid_product_image(message: Message, state: FSMContext, bot: Bot):
    """Rasm o'rniga boshqa narsa yuborilganini boshqarish"""
    await show_error_and_retry(
        message, state, bot,
        "⚠️ Iltimos, mahsulot rasmini yuboring.\n\n"
        "💡 Faqat rasm (photo) formatida yuborishingiz kerak.\n\n"
        "Rasmni qayta yuboring:"
    )


# ==================== TASDIQLASH VA YUBORISH ====================

@otchot_router.callback_query(F.data == "confirm_report", ReportState.waiting_for_confirmation)
async def confirm_and_send_report(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    """Hisobotni tasdiqlash va guruhga yuborish"""
    user_id = callback_query.from_user.id
    data = await state.get_data()
    
    assigned_group = await get_user_assigned_group(user_id)
    if not assigned_group:
        await callback_query.answer("❌ Guruh topilmadi!", show_alert=True)
        return
    
    group_id, group_name, topic_id, google_sheet_id = assigned_group
    
    is_tashkent = data.get('is_tashkent', False)
    sheet_name = get_daily_worksheet_name(is_tashkent)
    region_type_text = f"🏙️ Toshkent shahar ({sheet_name})" if is_tashkent else f"📍 Viloyat ({sheet_name})"
    
    additional_phone = data.get('additional_phone_number', '')
    additional_phone_line = f"📱 Qo'shimcha: {additional_phone}\n" if additional_phone and additional_phone != 'Mavjud emas' else ""
    
    seller_name = data.get('seller_name', 'Noma\'lum')
    delivery = data.get('delivery', 'Belgilanmagan')
    
    group_caption = REPORT_CAPTION_TEMPLATE.format(
        client_name=data.get('client_name'),
        phone_number=data.get('phone_number'),
        additional_phone_line=additional_phone_line,
        product_type=data.get('product_type'),
        client_location=data.get('client_location'),
        contract_id=data.get('contract_id'),
        contract_amount=data.get('contract_amount'),
        delivery=delivery,
        note=data.get('note', 'Yo\'q'),
        seller_name=seller_name,
        region_type_line=region_type_text,
        status_line="✅ Tasdiqlandi"
    )
    
    try:
        if topic_id:
            sent_message = await bot.send_photo(
                chat_id=group_id,
                photo=data.get('product_image_id'),
                caption=group_caption,
                reply_markup=get_report_confirmed_keyboard(),
                message_thread_id=topic_id
            )
        else:
            sent_message = await bot.send_photo(
                chat_id=group_id,
                photo=data.get('product_image_id'),
                caption=group_caption,
                reply_markup=get_report_confirmed_keyboard()
            )
        
        group_message_id = sent_message.message_id
        
        # Ma'lumotlar bazasiga saqlash
        report_data = {
            'client_name': data.get('client_name'),
            'phone_number': data.get('phone_number'),
            'additional_phone_number': additional_phone if additional_phone else 'Mavjud emas',
            'product_type': data.get('product_type'),
            'client_location': data.get('client_location'),
            'contract_id': data.get('contract_id'),
            'contract_amount': data.get('contract_amount'),
            'product_image_id': data.get('product_image_id'),
            'is_tashkent': is_tashkent,
            'delivery': delivery,
            'note': data.get('note', 'Yo\'q')
        }
        
        report_id = await add_sales_report(user_id, report_data, group_message_id, google_sheet_id)
        
        if google_sheet_id and report_id:
            try:
                sheet_info = await get_group_google_sheet(group_id)
                if sheet_info:
                    spreadsheet_id = sheet_info[2]
                    
                    sheet_data = {
                        **report_data,
                        'sender_full_name': seller_name
                    }
                    
                    # Kunlik sheetga saqlash (SH yoki VL)
                    sheet_success = save_report_to_sheets(
                        spreadsheet_id,
                        "",
                        sheet_data,
                        is_tashkent
                    )
                    
                    if sheet_success:
                        logging.info(f"✅ Hisobot Google Sheets'ga saqlandi: {sheet_name}")
                    else:
                        logging.warning("⚠️ Hisobot Google Sheets'ga saqlanmadi")
                    
                    # ALL DATA sheetga ham saqlash
                    all_data_spreadsheet_id = get_all_data_spreadsheet_id()
                    if all_data_spreadsheet_id:
                        all_data_success = save_report_to_all_data(
                            all_data_spreadsheet_id,
                            sheet_data,
                            is_tashkent
                        )
                        if all_data_success:
                            all_data_sheet_name = get_daily_all_data_worksheet_name()
                            logging.info(f"✅ Hisobot kunlik ALL DATA sheetga ham saqlandi: {all_data_sheet_name}")
                        else:
                            logging.warning("⚠️ Hisobot ALL DATA sheetga saqlanmadi")
                    
            except Exception as e:
                logging.error(f"Google Sheets'ga saqlashda xato: {e}")
        
        # Foydalanuvchiga xabar
        await callback_query.message.edit_caption(
            caption=(
                f"✅ Hisobot muvaffaqiyatli yuborildi!\n\n"
                f"🆔 Shartnoma raqami: {data.get('contract_id')}\n"
                f"🛍️ Mahsulot: {data.get('product_type')}\n"
                f"💰 Summa: {data.get('contract_amount')}\n"
                f"📍 Hudud: {data.get('client_location')}\n"
                f"🚛 Dastavka: {delivery}\n"
                f"📝 Izoh: {data.get('note', 'Yo\'q')}\n"
                f"👫 Sotuvchi: {seller_name}\n"
                f"🗂️ Sheet: {sheet_name}\n\n"
                f"✅ Hisobotingiz tasdiqlandi!"
            ),
            reply_markup=get_report_confirmed_keyboard()
        )
        
        await state.clear()
        
        logging.info(
            f"Hisobot muvaffaqiyatli yuborildi: User={user_id}, Contract={data.get('contract_id')}, "
            f"Toshkent={is_tashkent}, Sheet={sheet_name}, Seller={seller_name}, Delivery={delivery}"
        )
        await callback_query.answer("✅ Hisobot yuborildi!")
    
    except TelegramBadRequest as e:
        logging.error(f"Guruhga yuborishda xato: {e}")
        await callback_query.answer(
            "❌ Guruhga yuborishda xato. Admin bilan bog'laning.",
            show_alert=True
        )
    except Exception as e:
        logging.error(f"Hisobotni yuborishda xato: {e}")
        await callback_query.answer(
            "❌ Xatolik yuz berdi. Qaytadan urinib ko'ring.",
            show_alert=True
        )


# ==================== O'ZGARTIRISH HANDLERLARI ====================

@otchot_router.callback_query(F.data == "edit_report", ReportState.waiting_for_confirmation)
async def edit_report(callback_query: CallbackQuery, state: FSMContext):
    """Hisobotni o'zgartirish"""
    await callback_query.message.edit_caption(
        caption="✏️ Qaysi ma'lumotni o'zgartirmoqchisiz?",
        reply_markup=get_edit_selection_keyboard()
    )
    await state.set_state(ReportState.waiting_for_edit_selection)
    await callback_query.answer()


@otchot_router.callback_query(F.data == "back_to_confirmation", ReportState.waiting_for_edit_selection)
async def back_to_confirmation(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    """Tasdiqlashga qaytish"""
    data = await state.get_data()
    
    is_tashkent = data.get('is_tashkent', False)
    sheet_name = get_daily_worksheet_name(is_tashkent)
    region_type_text = f"🏙️ Hudud: Toshkent shahar ({sheet_name})" if is_tashkent else f"📍 Hudud: Viloyat ({sheet_name})"
    
    additional_phone = data.get('additional_phone_number', '')
    additional_phone_line = f"📱 Qo'shimcha: {additional_phone}\n" if additional_phone and additional_phone != 'Mavjud emas' else ""
    
    seller_name = data.get('seller_name', 'Noma\'lum')
    delivery = data.get('delivery', 'Belgilanmagan')
    
    confirmation_text = f"""📝 HISOBOT TASDIQLASH

👤 Mijoz: {data.get('client_name')}

📱 Telefon: {data.get('phone_number')}
{additional_phone_line}🛍️ Mahsulot: {data.get('product_type')}

📍 Manzil: {data.get('client_location')}

🆔 Shartnoma raqami: {data.get('contract_id')}

💰 Shartnoma summasi: {data.get('contract_amount')}

🚛 Dastavka: {delivery}

📝 Izoh: {data.get('note', 'Yo\'q')}

👫 Sotuvchi: {seller_name}

{region_type_text}

Ma'lumotlar to'g'rimi?"""
    
    await callback_query.message.edit_caption(
        caption=confirmation_text,
        reply_markup=get_report_confirmation_keyboard()
    )
    await state.set_state(ReportState.waiting_for_confirmation)
    await callback_query.answer()


@otchot_router.callback_query(F.data == "cancel_report", ReportState.waiting_for_confirmation)
async def cancel_report(callback_query: CallbackQuery, state: FSMContext):
    """Hisobotni bekor qilish"""
    await state.clear()
    await callback_query.message.delete()
    await callback_query.message.answer(
        "🚫 Hisobot bekor qilindi.\n\n"
        "🏠 Asosiy menyu:",
        reply_markup=get_main_menu_reply_keyboard()
    )
    await callback_query.answer()


@otchot_router.callback_query(F.data == "cancel_report_submission")
async def cancel_report_submission(callback_query: CallbackQuery, state: FSMContext):
    """Hisobot jarayonini bekor qilish"""
    await state.clear()
    try:
        await callback_query.message.delete()
    except:
        pass
    await callback_query.message.answer(
        "🚫 Hisobot jarayoni bekor qilindi.\n\n"
        "🏠 Asosiy menyu:",
        reply_markup=get_main_menu_reply_keyboard()
    )
    await callback_query.answer()


# ==================== GURUH HISOBOTLARI HANDLERLARI ====================

@otchot_router.callback_query(F.data == "confirm_report_action")
async def confirm_report_action(callback_query: CallbackQuery, bot: Bot):
    """Guruhda hisobotni tasdiqlash"""
    user_id = callback_query.from_user.id
    
    if user_id not in [ADMIN_ID, HELPER_ID]:
        await callback_query.answer("🚫 Sizda bu amalni bajarish uchun ruxsat yo'q.", show_alert=True)
        return
    
    message = callback_query.message
    group_message_id = message.message_id
    
    success = await update_report_status_in_db(group_message_id, "confirmed", user_id)
    
    if success:
        old_caption = message.caption or ""
        new_caption = old_caption.replace("⏳ Kutilmoqda...", "✅ Tasdiqlandi")
        
        try:
            await message.edit_caption(
                caption=new_caption,
                reply_markup=None
            )
            await callback_query.answer("✅ Hisobot tasdiqlandi!")
            logging.info(f"Hisobot tasdiqlandi: group_msg_id={group_message_id}, by={user_id}")
        except TelegramBadRequest as e:
            logging.error(f"Captionni yangilashda xato: {e}")
            await callback_query.answer("⚠️ Xabarni yangilashda xato", show_alert=True)
    else:
        await callback_query.answer("❌ Hisobotni tasdiqlashda xato", show_alert=True)


@otchot_router.callback_query(F.data == "reject_report_action")
async def reject_report_action(callback_query: CallbackQuery, bot: Bot):
    """Guruhda hisobotni rad etish"""
    user_id = callback_query.from_user.id
    
    if user_id not in [ADMIN_ID, HELPER_ID]:
        await callback_query.answer("🚫 Sizda bu amalni bajarish uchun ruxsat yo'q.", show_alert=True)
        return
    
    message = callback_query.message
    group_message_id = message.message_id
    
    success = await update_report_status_in_db(group_message_id, "rejected", user_id)
    
    if success:
        old_caption = message.caption or ""
        new_caption = old_caption.replace("⏳ Kutilmoqda...", "❌ Rad etildi")
        
        try:
            await message.edit_caption(
                caption=new_caption,
                reply_markup=get_rejection_reason_keyboard(user_id)
            )
            await callback_query.answer("❌ Hisobot rad etildi!")
            logging.info(f"Hisobot rad etildi: group_msg_id={group_message_id}, by={user_id}")
        except TelegramBadRequest as e:
            logging.error(f"Captionni yangilashda xato: {e}")
            await callback_query.answer("⚠️ Xabarni yangilashda xato", show_alert=True)
    else:
        await callback_query.answer("❌ Hisobotni rad etishda xato", show_alert=True)


@otchot_router.callback_query(F.data.startswith("contact_helper_"))
async def contact_helper(callback_query: CallbackQuery):
    """Helper bilan bog'lanish"""
    helper_id = int(callback_query.data.split("_")[-1])
    await callback_query.message.answer(
        "📞 Hisobotingiz rad etildi. Sababini bilish uchun quyidagi tugmani bosing:",
        reply_markup=get_contact_helper_keyboard(helper_id)
    )
    await callback_query.answer()


@otchot_router.callback_query(F.data == "status_confirmed_noop")
async def status_confirmed_noop(callback_query: CallbackQuery):
    """Tasdiqlangan hisobotdagi tugma bosilganda"""
    await callback_query.answer("✅ Bu hisobot allaqachon yuborilgan", show_alert=False)


# ==================== LOGGING SOZLAMALARI ====================

logging.info("🚀 Otchot moduli muvaffaqiyatli yuklandi")
logging.info("📊 Kunlik sheetlar tizimi faollashtirildi: SH/VL DD.MM.YYYY")
logging.info("🚛 YANGI: Dastavka maydoni qo'shildi")