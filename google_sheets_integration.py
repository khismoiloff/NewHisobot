import gspread
from google.oauth2.service_account import Credentials
import logging
from datetime import datetime, date, timedelta
import json
import os
from typing import Dict, List, Tuple, Optional

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

GOOGLE_SHEETS_CREDENTIALS_FILE = "credentials.json"

# ==================== USTUNLAR RO'YXATI (YANGILANGAN) ====================

COLUMN_HEADERS = [
    "№",
    "Mijoz ismi",
    "Telefon raqami",
    "Qo'shimcha telefon", 
    "Mahsulot nomi",
    "Jo'natma turi",
    "Dastavka",  # YANGI USTUN
    "Izoh", 
    "Mijoz manzili",
    "Shartnoma imzolangan sana",
    "Yuborilgan sana",
    "Shartnoma raqami",
    "Shartnoma summasi",
    "Sotuvchi ismi"
]

LINKS_COLUMN_HEADERS = [
    "№",
    "Link",
    "Qo'shilgan sana",
    "Qo'shgan admin",
    "Izoh"
]

ALL_DATA_COLUMN_HEADERS = [
    "№",
    "Mijoz ismi",
    "Telefon raqami",
    "Qo'shimcha telefon", 
    "Mahsulot nomi",
    "Jo'natma turi",
    "Dastavka",  # YANGI USTUN
    "Izoh", 
    "Mijoz manzili",
    "Shartnoma imzolangan sana",
    "Yuborilgan sana",
    "Shartnoma raqami",
    "Shartnoma summasi",
    "Sotuvchi ismi",
    "Manba sheet"  # Hudud turi o'rniga Manba sheet
]

ALL_DATA_WORKSHEET_NAME = "ALL DATA"  # Legacy - endi kun bilan ishlatiladi

# ==================== GOOGLE SHEETS CLIENT ====================

def get_google_sheets_client():
    """Google Sheets clientni olish"""
    try:
        if not os.path.exists(GOOGLE_SHEETS_CREDENTIALS_FILE):
            logging.error(f"❌ Credentials fayl topilmadi: {GOOGLE_SHEETS_CREDENTIALS_FILE}")
            return None
        
        credentials = Credentials.from_service_account_file(
            GOOGLE_SHEETS_CREDENTIALS_FILE,
            scopes=SCOPES
        )
        client = gspread.authorize(credentials)
        logging.info("✅ Google Sheets client muvaffaqiyatli yaratildi")
        return client
    
    except Exception as e:
        logging.error(f"❌ Google Sheets client yaratishda xato: {e}")
        return None


# ==================== KUNLIK SHEET TIZIMLARI ====================

def get_daily_worksheet_name(is_tashkent: bool = False) -> str:
    """
    Kunlik worksheet nomini generatsiya qilish
    Toshkent shahar uchun: SH 28.11.2025
    Viloyat uchun: VL 28.11.2025
    """
    today = datetime.now()
    date_str = today.strftime('%d.%m.%Y')
    
    if is_tashkent:
        return f"SH {date_str}"
    else:
        return f"VL {date_str}"


def get_daily_all_data_worksheet_name() -> str:
    """
    Kunlik ALL DATA worksheet nomini generatsiya qilish
    Format: ALL DATA 06.12.2025
    """
    today = datetime.now()
    date_str = today.strftime('%d.%m.%Y')
    return f"ALL DATA {date_str}"


def is_tashkent_region(region: str) -> bool:
    """
    Tanlangan hudud Toshkent shahar ekanligini tekshirish
    """
    if not region:
        return False
    
    tashkent_keywords = [
        "toshkent shahar", 
        "toshkent shaxar",
        "toshkent sh",
        "toshkent shahar",
        "toshkent city",
        "тошкент шаҳар",
        "ташкент"
    ]
    
    region_lower = region.lower().strip()
    
    for keyword in tashkent_keywords:
        if keyword in region_lower:
            return True
    
    if region_lower == "toshkent shahar":
        return True
    
    return False


def get_or_create_daily_worksheet(spreadsheet_id: str, is_tashkent: bool = False):
    """
    Kunlik worksheet olish yoki yaratish.
    Yangi yaratilgan sheet har doim eng chapga (index=0) qo'yiladi.
    """
    try:
        client = get_google_sheets_client()
        if not client:
            logging.error("❌ Google Sheets client yaratilmadi")
            return None
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        logging.info(f"📄 Spreadsheet ochildi: {spreadsheet.title}")
        
        worksheet_name = get_daily_worksheet_name(is_tashkent)
        
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            logging.info(f"📋 Mavjud kunlik worksheet topildi: '{worksheet_name}'")
            
            existing_headers = worksheet.row_values(1)
            if not existing_headers or len(existing_headers) < len(COLUMN_HEADERS):
                logging.info("🔧 Sarlavhalar yangilanmoqda...")
                worksheet.clear()
                worksheet.append_row(COLUMN_HEADERS)
                format_worksheet_headers(worksheet)
        
        except gspread.WorksheetNotFound:
            logging.info(f"➕ Yangi kunlik worksheet yaratilmoqda (Eng Chapga): '{worksheet_name}'")
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=1000,
                cols=len(COLUMN_HEADERS),
                index=0
            )
            
            worksheet.append_row(COLUMN_HEADERS)
            format_worksheet_headers(worksheet)
            
            logging.info(f"✅ Yangi kunlik worksheet yaratildi: '{worksheet_name}'")
        
        return worksheet
    
    except Exception as e:
        logging.error(f"❌ Kunlik worksheet olishda xato: {e}")
        return None


def get_worksheet(spreadsheet_id: str, worksheet_name: str):
    """Oddiy worksheet olish (kunlik emas)"""
    try:
        client = get_google_sheets_client()
        if not client:
            logging.error("❌ Google Sheets client yaratilmadi")
            return None
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        logging.info(f"📄 Spreadsheet ochildi: {spreadsheet.title}")
        
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            logging.info(f"📋 Worksheet topildi: '{worksheet_name}'")
            
            existing_headers = worksheet.row_values(1)
            if not existing_headers or len(existing_headers) < len(COLUMN_HEADERS):
                logging.info("🔧 Sarlavhalar yangilanmoqda...")
                worksheet.clear()
                worksheet.append_row(COLUMN_HEADERS)
                format_worksheet_headers(worksheet)
        
        except gspread.WorksheetNotFound:
            logging.info(f"➕ Yangi worksheet yaratilmoqda: '{worksheet_name}'")
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=1000,
                cols=len(COLUMN_HEADERS)
            )
            
            worksheet.append_row(COLUMN_HEADERS)
            format_worksheet_headers(worksheet)
            
            logging.info(f"✅ Yangi worksheet yaratildi va formatlandi: '{worksheet_name}'")
        
        return worksheet
    
    except Exception as e:
        logging.error(f"❌ Worksheet olishda xato: {e}")
        return None


# ==================== FORMATLASH ====================

def format_worksheet_headers(worksheet):
    """Sarlavhalarni formatlash"""
    try:
        header_range = f"A1:{chr(64 + len(COLUMN_HEADERS))}1"
        
        worksheet.format(header_range, {
            'backgroundColor': {
                'red': 0.2,
                'green': 0.4,
                'blue': 0.8
            },
            'textFormat': {
                'bold': True,
                'foregroundColor': {
                    'red': 1.0,
                    'green': 1.0,
                    'blue': 1.0
                },
                'fontSize': 11
            },
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE'
        })
        
        worksheet.columns_auto_resize(0, len(COLUMN_HEADERS) - 1)
        
        worksheet.format('A:A', {
            'horizontalAlignment': 'CENTER',
            'textFormat': {'bold': True}
        })
        
        worksheet.format('I:K', {
            'horizontalAlignment': 'CENTER'
        })
        
        logging.info("✅ Sarlavhalar muvaffaqiyatli formatlandi")
    
    except Exception as e:
        logging.error(f"❌ Sarlavhalarni formatlashda xato: {e}")


def format_new_row(worksheet, row_index: int, row_number: int):
    """Yangi qatorni formatlash"""
    try:
        row_range = f"A{row_index}:{chr(64 + len(COLUMN_HEADERS))}{row_index}"
        
        if row_number % 2 == 0:
            background_color = {'red': 0.95, 'green': 0.95, 'blue': 0.95}
        else:
            background_color = {'red': 1.0, 'green': 1.0, 'blue': 1.0}
        
        if row_number == 1:
            background_color = {'red': 0.9, 'green': 0.95, 'blue': 1.0}
        
        worksheet.format(row_range, {
            'backgroundColor': background_color,
            'borders': {
                'top': {'style': 'SOLID', 'width': 1},
                'bottom': {'style': 'SOLID', 'width': 1},
                'left': {'style': 'SOLID', 'width': 1},
                'right': {'style': 'SOLID', 'width': 1}
            }
        })
        
        worksheet.format(f'A{row_index}', {
            'horizontalAlignment': 'CENTER',
            'textFormat': {'bold': True}
        })
        
        worksheet.format(f'I{row_index}:K{row_index}', {
            'horizontalAlignment': 'CENTER'
        })
    
    except Exception as e:
        logging.error(f"❌ Qatorni formatlashda xato: {e}")


def format_links_worksheet_headers(worksheet):
    """Linklar sarlavhalarini formatlash"""
    try:
        header_range = f"A1:{chr(64 + len(LINKS_COLUMN_HEADERS))}1"
        
        worksheet.format(header_range, {
            'backgroundColor': {
                'red': 0.2,
                'green': 0.6,
                'blue': 0.4
            },
            'textFormat': {
                'bold': True,
                'foregroundColor': {
                    'red': 1.0,
                    'green': 1.0,
                    'blue': 1.0
                },
                'fontSize': 11
            },
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE'
        })
        
        worksheet.columns_auto_resize(0, len(LINKS_COLUMN_HEADERS) - 1)
        
        logging.info("✅ Linklar sarlavhalari formatlandi")
    
    except Exception as e:
        logging.error(f"❌ Linklar sarlavhalarini formatlashda xato: {e}")


def format_all_data_worksheet_headers(worksheet):
    """ALL DATA sarlavhalarni formatlash"""
    try:
        header_range = f"A1:{chr(64 + len(ALL_DATA_COLUMN_HEADERS))}1"
        
        worksheet.format(header_range, {
            'backgroundColor': {
                'red': 0.1,
                'green': 0.3,
                'blue': 0.6
            },
            'textFormat': {
                'bold': True,
                'foregroundColor': {
                    'red': 1.0,
                    'green': 1.0,
                    'blue': 1.0
                },
                'fontSize': 11
            },
            'horizontalAlignment': 'CENTER',
            'verticalAlignment': 'MIDDLE'
        })
        
        worksheet.columns_auto_resize(0, len(ALL_DATA_COLUMN_HEADERS) - 1)
        
        logging.info("✅ ALL DATA sarlavhalar formatlandi")
    except Exception as e:
        logging.warning(f"⚠️ ALL DATA sarlavhalarni formatlashda xato: {e}")


# ==================== HISOBOTLARNI SAQLASH ====================

def get_next_row_number(worksheet) -> int:
    """Keyingi tartib raqamini olish"""
    try:
        all_values = worksheet.get_all_values()
        
        if len(all_values) <= 1:
            return 1
        
        last_row = all_values[-1]
        if last_row and len(last_row) > 0 and last_row[0].isdigit():
            return int(last_row[0]) + 1
        else:
            return len(all_values)
    
    except Exception as e:
        logging.error(f"❌ Tartib raqamini aniqlashda xato: {e}")
        return 1


def save_report_to_daily_sheet(spreadsheet_id: str, report_data: dict, is_tashkent: bool = False) -> bool:
    """
    Hisobotni kunlik sheetga saqlash
    Toshkent shahar uchun: SH DD.MM.YYYY sheetga
    Viloyat uchun: VL DD.MM.YYYY sheetga
    """
    try:
        worksheet = get_or_create_daily_worksheet(spreadsheet_id, is_tashkent)
        if not worksheet:
            logging.error("❌ Kunlik worksheet topilmadi yoki yaratilmadi")
            return False
        
        row_number = get_next_row_number(worksheet)
        
        current_date = datetime.now().strftime('%d.%m.%Y')
        
        row_data = [
            str(row_number),  # A: № (Tartib raqami)
            report_data.get('client_name', ''),  # B: Mijoz ismi
            report_data.get('phone_number', ''),  # C: Telefon raqami
            report_data.get('additional_phone_number', ''),  # D: Qo'shimcha telefon
            report_data.get('product_type', ''),  # E: Mahsulot nomi
            '',  # F: Jo'natma turi (bo'sh)
            report_data.get('delivery', ''),  # G: Dastavka (YANGI)
            report_data.get('note', ''),  # H: Izoh
            report_data.get('client_location', ''),  # I: Mijoz manzili
            current_date,  # J: Shartnoma imzolangan sana
            '',  # K: Yuborilgan sana (bo'sh)
            report_data.get('contract_id', ''),  # L: Shartnoma raqami
            report_data.get('contract_amount', ''),  # M: Shartnoma summasi
            report_data.get('sender_full_name', '')  # N: Sotuvchi ismi
        ]
        
        worksheet.append_row(row_data)
        
        new_row_index = len(worksheet.get_all_values())
        format_new_row(worksheet, new_row_index, row_number)
        
        sheet_type = "Toshkent shahar (SH)" if is_tashkent else "Viloyat (VL)"
        worksheet_name = get_daily_worksheet_name(is_tashkent)
        
        logging.info(
            f"✅ Hisobot #{row_number} {sheet_type} sheetga saqlandi: '{worksheet_name}' - "
            f"{report_data.get('sender_full_name', 'Noma\'lum')} - "
            f"{report_data.get('product_type', 'Noma\'lum mahsulot')} - "
            f"{report_data.get('contract_amount', 'Noma\'lum summa')}"
        )
        
        return True
    
    except Exception as e:
        logging.error(f"❌ Kunlik sheetga saqlashda xato: {e}")
        return False


def save_report_to_sheets(spreadsheet_id: str, worksheet_name: str, report_data: dict, is_tashkent: bool = None) -> bool:
    """
    Hisobotni Google Sheets'ga saqlash
    Agar is_tashkent parametri berilsa, kunlik sheetga saqlaydi
    """
    try:
        if is_tashkent is not None:
            return save_report_to_daily_sheet(spreadsheet_id, report_data, is_tashkent)
        
        client_location = report_data.get('client_location', '')
        detected_is_tashkent = is_tashkent_region(client_location)
        
        return save_report_to_daily_sheet(spreadsheet_id, report_data, detected_is_tashkent)
    
    except Exception as e:
        logging.error(f"❌ Google Sheets'ga saqlashda xato: {e}")
        return False


# ==================== LINK SAQLASH FUNKSIYALARI ====================

def get_or_create_links_worksheet(spreadsheet_id: str):
    """
    Linklar uchun worksheet olish yoki yaratish
    """
    try:
        client = get_google_sheets_client()
        if not client:
            logging.error("❌ Google Sheets client yaratilmadi")
            return None
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        logging.info(f"📄 Spreadsheet ochildi: {spreadsheet.title}")
        
        worksheet_name = "Linklar"
        
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            logging.info(f"📋 Linklar worksheet topildi: '{worksheet_name}'")
            
            existing_headers = worksheet.row_values(1)
            if not existing_headers or len(existing_headers) < len(LINKS_COLUMN_HEADERS):
                logging.info("🔧 Linklar sarlavhalari yangilanmoqda...")
                worksheet.clear()
                worksheet.append_row(LINKS_COLUMN_HEADERS)
                format_links_worksheet_headers(worksheet)
        
        except gspread.WorksheetNotFound:
            logging.info(f"➕ Yangi Linklar worksheet yaratilmoqda: '{worksheet_name}'")
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=1000,
                cols=len(LINKS_COLUMN_HEADERS)
            )
            
            worksheet.append_row(LINKS_COLUMN_HEADERS)
            format_links_worksheet_headers(worksheet)
            
            logging.info(f"✅ Linklar worksheet yaratildi: '{worksheet_name}'")
        
        return worksheet
    
    except Exception as e:
        logging.error(f"❌ Linklar worksheet olishda xato: {e}")
        return None


def save_link_to_sheets(spreadsheet_id: str, link: str, admin_name: str, note: str = "") -> Tuple[bool, str]:
    """
    Linkni Google Sheets ga saqlash
    """
    try:
        worksheet = get_or_create_links_worksheet(spreadsheet_id)
        if not worksheet:
            return False, "❌ Linklar worksheet ochilmadi"
        
        all_values = worksheet.get_all_values()
        row_count = len(all_values)
        
        new_row_number = row_count
        
        current_datetime = datetime.now().strftime('%d.%m.%Y %H:%M')
        
        row_data = [
            new_row_number,
            link,
            current_datetime,
            admin_name,
            note if note else "-"
        ]
        
        worksheet.append_row(row_data, value_input_option='USER_ENTERED')
        
        logging.info(f"✅ Link saqlandi: {link[:50]}... (№{new_row_number})")
        
        return True, f"✅ Link muvaffaqiyatli saqlandi!\n📊 Tartib raqami: {new_row_number}\n📅 Sana: {current_datetime}"
    
    except Exception as e:
        logging.error(f"❌ Linkni saqlashda xato: {e}")
        return False, f"❌ Linkni saqlashda xato: {str(e)}"


def get_all_links_from_sheets(spreadsheet_id: str) -> Tuple[bool, List[Dict] | str]:
    """
    Barcha linklar ro'yxatini olish
    """
    try:
        worksheet = get_or_create_links_worksheet(spreadsheet_id)
        if not worksheet:
            return False, "❌ Linklar worksheet ochilmadi"
        
        all_values = worksheet.get_all_values()
        
        if len(all_values) <= 1:
            return True, []
        
        links = []
        for row in all_values[1:]:
            if len(row) >= 4:
                links.append({
                    'number': row[0],
                    'link': row[1],
                    'date': row[2],
                    'admin': row[3],
                    'note': row[4] if len(row) > 4 else "-"
                })
        
        return True, links
    
    except Exception as e:
        logging.error(f"❌ Linklar olishda xato: {e}")
        return False, f"❌ Linklar olishda xato: {str(e)}"


def get_links_count(spreadsheet_id: str) -> int:
    """Linklar sonini olish"""
    try:
        worksheet = get_or_create_links_worksheet(spreadsheet_id)
        if not worksheet:
            return 0
        
        all_values = worksheet.get_all_values()
        return max(0, len(all_values) - 1)
    
    except Exception as e:
        logging.error(f"❌ Linklar sonini olishda xato: {e}")
        return 0


# ==================== ALL DATA ====================

def get_or_create_all_data_worksheet(spreadsheet_id: str):
    """
    Kunlik ALL DATA worksheet olish yoki yaratish
    Format: ALL DATA 06.12.2025
    Barcha hisobotlar kun bo'yicha alohida sheetlarga saqlanadi
    """
    try:
        client = get_google_sheets_client()
        if not client:
            logging.error("❌ Google Sheets client yaratilmadi")
            return None
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        logging.info(f"📄 ALL DATA Spreadsheet ochildi: {spreadsheet.title}")
        
        # Kunlik worksheet nomini olish
        worksheet_name = get_daily_all_data_worksheet_name()
        
        try:
            # Mavjud worksheet ni tekshirish
            worksheet = spreadsheet.worksheet(worksheet_name)
            logging.info(f"📋 Mavjud kunlik ALL DATA worksheet topildi: '{worksheet_name}'")
            
            # Sarlavhalarni tekshirish
            existing_headers = worksheet.row_values(1)
            if not existing_headers or len(existing_headers) < len(ALL_DATA_COLUMN_HEADERS):
                logging.info("🔧 ALL DATA sarlavhalar yangilanmoqda...")
                worksheet.clear()
                worksheet.append_row(ALL_DATA_COLUMN_HEADERS)
                format_all_data_worksheet_headers(worksheet)
        
        except gspread.WorksheetNotFound:
            # Yangi kunlik ALL DATA worksheet yaratish (eng chapga)
            logging.info(f"➕ Yangi kunlik ALL DATA worksheet yaratilmoqda: '{worksheet_name}'")
            worksheet = spreadsheet.add_worksheet(
                title=worksheet_name,
                rows=5000,
                cols=len(ALL_DATA_COLUMN_HEADERS),
                index=0  # Eng chapga qo'yish
            )
            
            # Sarlavhalarni qo'shish
            worksheet.append_row(ALL_DATA_COLUMN_HEADERS)
            format_all_data_worksheet_headers(worksheet)
            
            logging.info(f"✅ Kunlik ALL DATA worksheet yaratildi: '{worksheet_name}'")
        
        return worksheet
    
    except Exception as e:
        logging.error(f"❌ ALL DATA worksheet olishda xato: {e}")
        return None


def save_report_to_all_data(spreadsheet_id: str, report_data: dict, is_tashkent: bool = False) -> bool:
    """
    Hisobotni kunlik ALL DATA sheetga saqlash
    Format: ALL DATA 06.12.2025
    Barcha hisobotlar kun bo'yicha alohida sheetlarga saqlanadi
    """
    try:
        worksheet = get_or_create_all_data_worksheet(spreadsheet_id)
        if not worksheet:
            logging.error("❌ ALL DATA worksheet topilmadi")
            return False
        
        all_values = worksheet.get_all_values()
        if len(all_values) <= 1:
            row_number = 1
        else:
            last_row = all_values[-1]
            if last_row and len(last_row) > 0 and str(last_row[0]).isdigit():
                row_number = int(last_row[0]) + 1
            else:
                row_number = len(all_values)
        
        current_date = datetime.now().strftime('%d.%m.%Y')
        
        # Manba sheet nomini aniqlash (SH yoki VL)
        source_sheet_name = get_daily_worksheet_name(is_tashkent)
        
        # ALL DATA worksheet nomi
        all_data_sheet_name = get_daily_all_data_worksheet_name()
        
        row_data = [
            str(row_number),  # A: № (Tartib raqami)
            report_data.get('client_name', ''),  # B: Mijoz ismi
            report_data.get('phone_number', ''),  # C: Telefon raqami
            report_data.get('additional_phone_number', ''),  # D: Qo'shimcha telefon
            report_data.get('product_type', ''),  # E: Mahsulot nomi
            '',  # F: Jo'natma turi (bo'sh)
            report_data.get('delivery', ''),  # G: Dastavka
            report_data.get('note', ''),  # H: Izoh
            report_data.get('client_location', ''),  # I: Mijoz manzili
            current_date,  # J: Shartnoma imzolangan sana
            '',  # K: Yuborilgan sana (bo'sh)
            report_data.get('contract_id', ''),  # L: Shartnoma raqami
            report_data.get('contract_amount', ''),  # M: Shartnoma summasi
            report_data.get('sender_full_name', ''),  # N: Sotuvchi ismi
            source_sheet_name  # O: Manba sheet (SH/VL kun raqami bilan)
        ]
        
        worksheet.append_row(row_data)
        
        logging.info(
            f"✅ Hisobot #{row_number} kunlik ALL DATA sheetga saqlandi: '{all_data_sheet_name}' - "
            f"{report_data.get('sender_full_name', 'Noma\'lum')} - "
            f"Manba: {source_sheet_name}"
        )
        
        return True
    
    except Exception as e:
        logging.error(f"❌ ALL DATA sheetga saqlashda xato: {e}")
        return False


def get_all_data_stats(spreadsheet_id: str) -> Dict:
    """Kunlik ALL DATA sheet statistikasini olish"""
    try:
        worksheet = get_or_create_all_data_worksheet(spreadsheet_id)
        if not worksheet:
            return {'total': 0, 'tashkent': 0, 'regions': 0, 'sheet_name': ''}
        
        all_values = worksheet.get_all_values()
        sheet_name = get_daily_all_data_worksheet_name()
        
        if len(all_values) <= 1:
            return {'total': 0, 'tashkent': 0, 'regions': 0, 'sheet_name': sheet_name}
        
        total = len(all_values) - 1
        tashkent = 0
        regions = 0
        
        for row in all_values[1:]:
            # Manba sheet ustuni (oxirgi ustun)
            if len(row) >= 15:
                source_sheet = row[14]  # Manba sheet ustuni
                if source_sheet.startswith("SH"):
                    tashkent += 1
                elif source_sheet.startswith("VL"):
                    regions += 1
        
        return {
            'total': total,
            'tashkent': tashkent,
            'regions': regions,
            'sheet_name': sheet_name
        }
    
    except Exception as e:
        logging.error(f"❌ ALL DATA statistikani olishda xato: {e}")
        return {'total': 0, 'tashkent': 0, 'regions': 0, 'sheet_name': ''}


# ==================== TEST VA STATISTIKA ====================

def test_all_data_sheet_connection(spreadsheet_id: str) -> Tuple[bool, str]:
    """
    Kunlik ALL DATA Google Sheets ulanishini test qilish
    """
    try:
        worksheet = get_or_create_all_data_worksheet(spreadsheet_id)
        if not worksheet:
            return False, "❌ ALL DATA worksheet yaratib bo'lmadi yoki ulanish xatosi"
        
        test_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        all_data_sheet_name = get_daily_all_data_worksheet_name()
        
        test_data = {
            'client_name': f'TEST - ALL DATA Test mijoz',
            'phone_number': '+998901234567',
            'additional_phone_number': '+998991234567',
            'contract_id': f'TEST-ALLDATA-{test_timestamp}',
            'product_type': 'TEST - Samsung Galaxy A54 128GB',
            'client_location': 'TEST - Toshkent shahar, Yunusobod tumani',
            'contract_amount': 'TEST - 5,000,000 so\'m',
            'sender_full_name': 'TEST - Sotuvchi',
            'note': 'TEST - Bu test izoh',
            'delivery': 'TEST - Bepul dastavka',
            'status': 'Tasdiqlandi'
        }
        
        success = save_report_to_all_data(spreadsheet_id, test_data, is_tashkent=True)
        
        if success:
            all_values = worksheet.get_all_values()
            last_row = all_values[-1] if len(all_values) > 1 else []
            
            success_message = (
                f"✅ KUNLIK ALL DATA TEST MUVAFFAQIYATLI BAJARILDI!\n\n"
                f"📊 **Sheet:** {all_data_sheet_name}\n\n"
                f"📋 Qo'shilgan test ma'lumotlari:\n"
                f"• Tartib raqami: #{last_row[0] if last_row else 'N/A'}\n"
                f"• Mijoz: {test_data['client_name']}\n"
                f"• Telefon: {test_data['phone_number']}\n"
                f"• Qo'shimcha telefon: {test_data['additional_phone_number']}\n"
                f"• Mahsulot: {test_data['product_type']}\n"
                f"• Dastavka: {test_data['delivery']}\n"
                f"• Shartnoma: {test_data['contract_id']}\n"
                f"• Summa: {test_data['contract_amount']}\n"
                f"• Manzil: {test_data['client_location']}\n"
                f"• Sotuvchi: {test_data['sender_full_name']}\n"
                f"• Izoh: {test_data['note']}\n"
                f"• Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"📊 Jami qatorlar: {len(all_values)} (sarlavha bilan)\n"
                f"📈 Ma'lumotlar qatori: {len(all_values) - 1}\n\n"
                f"🔗 Google Sheets'da tekshiring!"
            )
            
            return True, success_message
        else:
            return False, "❌ Test ma'lumotlarini qo'shishda xatolik yuz berdi"
    
    except Exception as e:
        error_msg = f"❌ ALL DATA test qilishda xato: {str(e)}"
        logging.error(error_msg)
        return False, error_msg


def test_google_sheets_connection(spreadsheet_id: str, worksheet_name: str, is_tashkent: bool = False) -> Tuple[bool, str]:
    """
    Google Sheets ulanishini test qilish
    """
    try:
        worksheet = get_or_create_daily_worksheet(spreadsheet_id, is_tashkent)
        if not worksheet:
            return False, "❌ Kunlik worksheet yaratib bo'lmadi yoki ulanish xatosi"
        
        test_timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        sheet_type = "Toshkent shahar" if is_tashkent else "Viloyat"
        worksheet_name_generated = get_daily_worksheet_name(is_tashkent)
        
        test_data = {
            'client_name': f'TEST - Abdullayev Akmal ({sheet_type})',
            'phone_number': '+998901234567',
            'additional_phone_number': '+998991234567',
            'contract_id': f'TEST-{test_timestamp}',
            'product_type': f'TEST - Samsung Galaxy A54 128GB ({sheet_type})',
            'client_location': f'TEST - {sheet_type}, Chilonzor tumani',
            'contract_amount': 'TEST - 5,000,000 so\'m',
            'sender_full_name': 'TEST - Sotuvchi',
            'note': 'TEST - Bu test izoh',
            'delivery': 'TEST - Bepul dastavka',
            'status': 'Tasdiqlandi'
        }
        
        success = save_report_to_daily_sheet(spreadsheet_id, test_data, is_tashkent)
        
        if success:
            all_values = worksheet.get_all_values()
            last_row = all_values[-1] if len(all_values) > 1 else []
            
            success_message = (
                f"✅ TEST MUVAFFAQIYATLI BAJARILDI!\n\n"
                f"📊 **Sheet turi:** {sheet_type}\n"
                f"📋 **Worksheet nomi:** {worksheet_name_generated}\n\n"
                f"📋 Qo'shilgan test ma'lumotlari:\n"
                f"• Tartib raqami: #{last_row[0] if last_row else 'N/A'}\n"
                f"• Mijoz: {test_data['client_name']}\n"
                f"• Telefon: {test_data['phone_number']}\n"
                f"• Qo'shimcha telefon: {test_data['additional_phone_number']}\n"
                f"• Mahsulot: {test_data['product_type']}\n"
                f"• Dastavka: {test_data['delivery']}\n"
                f"• Shartnoma: {test_data['contract_id']}\n"
                f"• Summa: {test_data['contract_amount']}\n"
                f"• Manzil: {test_data['client_location']}\n"
                f"• Sotuvchi: {test_data['sender_full_name']}\n"
                f"• Izoh: {test_data['note']}\n"
                f"• Sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"📊 Jami qatorlar: {len(all_values)} (sarlavha bilan)\n"
                f"📈 Ma'lumotlar qatori: {len(all_values) - 1}\n\n"
                f"🔗 Google Sheets'da tekshiring!"
            )
            
            return True, success_message
        else:
            return False, "❌ Test ma'lumotlarini qo'shishda xatolik yuz berdi"
    
    except Exception as e:
        error_msg = f"❌ Test qilishda xato: {str(e)}"
        logging.error(error_msg)
        return False, error_msg


def get_daily_sheets_list(spreadsheet_id: str) -> List[Dict]:
    """
    Spreadsheetdagi barcha kunlik sheetlar ro'yxatini olish
    """
    try:
        client = get_google_sheets_client()
        if not client:
            return []
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheets = spreadsheet.worksheets()
        
        daily_sheets = []
        for ws in worksheets:
            title = ws.title
            if title.startswith('SH ') or title.startswith('VL '):
                sheet_type = "Toshkent shahar" if title.startswith('SH ') else "Viloyat"
                try:
                    row_count = len(ws.get_all_values()) - 1
                except:
                    row_count = 0
                
                daily_sheets.append({
                    'name': title,
                    'type': sheet_type,
                    'row_count': row_count
                })
        
        logging.info(f"📊 {len(daily_sheets)} ta kunlik sheet topildi")
        return daily_sheets
    
    except Exception as e:
        logging.error(f"❌ Kunlik sheetlar ro'yxatini olishda xato: {e}")
        return []


def get_reports_statistics(spreadsheet_id: str, worksheet_name: str) -> Dict:
    """Hisobotlar statistikasini olish"""
    try:
        worksheet = get_worksheet(spreadsheet_id, worksheet_name)
        if not worksheet:
            logging.error("❌ Worksheet topilmadi")
            return {}
        
        all_records = worksheet.get_all_records()
        
        if not all_records:
            logging.info("ℹ️ Google Sheets'da ma'lumotlar topilmadi")
            return {
                'total_reports': 0,
                'sellers_stats': {},
                'monthly_stats': {},
                'daily_stats': {},
                'product_stats': {},
                'location_stats': {},
                'tashkent_count': 0,
                'viloyat_count': 0,
                'last_updated': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
            }
        
        total_reports = len(all_records)
        sellers_stats = {}
        monthly_stats = {}
        daily_stats = {}
        product_stats = {}
        location_stats = {}
        
        tashkent_count = 0
        viloyat_count = 0
        
        for record in all_records:
            seller = record.get('Sotuvchi ismi', '').strip()
            if seller and seller != '' and 'TEST' not in seller.upper():
                sellers_stats[seller] = sellers_stats.get(seller, 0) + 1
            
            product = record.get('Mahsulot nomi', '').strip()
            if product and product != '' and 'TEST' not in product.upper():
                product_stats[product] = product_stats.get(product, 0) + 1
            
            location = record.get('Mijoz manzili', '').strip()
            if location and 'TEST' not in location.upper():
                if is_tashkent_region(location):
                    tashkent_count += 1
                else:
                    viloyat_count += 1
                
                if 'shahar' in location.lower():
                    city = location.split('shahar')[0].strip() + ' shahar'
                elif 'viloyat' in location.lower():
                    city = location.split('viloyat')[0].strip() + ' viloyat'
                else:
                    city = location.split(',')[0].strip() if ',' in location else 'Boshqa'
                
                location_stats[city] = location_stats.get(city, 0) + 1
            
            try:
                date_str = record.get('Shartnoma imzolangan sana', '').strip()
                if date_str:
                    if ' ' in date_str:
                        date_str = date_str.split(' ')[0]
                    
                    date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                    
                    month_key = date_obj.strftime('%Y-%m')
                    monthly_stats[month_key] = monthly_stats.get(month_key, 0) + 1
                    
                    day_key = date_obj.strftime('%Y-%m-%d')
                    daily_stats[day_key] = daily_stats.get(day_key, 0) + 1
            
            except ValueError as e:
                logging.warning(f"⚠️ Sanani tahlil qilishda xato: {date_str} - {e}")
                continue
        
        top_sellers = dict(sorted(sellers_stats.items(), key=lambda x: x[1], reverse=True)[:10])
        top_products = dict(sorted(product_stats.items(), key=lambda x: x[1], reverse=True)[:10])
        top_locations = dict(sorted(location_stats.items(), key=lambda x: x[1], reverse=True)[:10])
        
        today = date.today()
        last_30_days = {}
        for i in range(30):
            day = today - timedelta(days=i)
            day_key = day.strftime('%Y-%m-%d')
            last_30_days[day_key] = daily_stats.get(day_key, 0)
        
        statistics = {
            'total_reports': total_reports,
            'sellers_stats': sellers_stats,
            'top_sellers': top_sellers,
            'monthly_stats': monthly_stats,
            'daily_stats': daily_stats,
            'last_30_days': last_30_days,
            'product_stats': product_stats,
            'top_products': top_products,
            'location_stats': location_stats,
            'top_locations': top_locations,
            'tashkent_count': tashkent_count,
            'viloyat_count': viloyat_count,
            'last_updated': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }
        
        logging.info(f"📊 Statistika muvaffaqiyatli olindi: {total_reports} ta yozuv")
        return statistics
    
    except Exception as e:
        logging.error(f"❌ Statistika olishda xato: {e}")
        return {}


def get_reports_by_date_range(spreadsheet_id: str, worksheet_name: str, start_date: str, end_date: str) -> List[Dict]:
    """Sana oralig'idagi hisobotlarni olish"""
    try:
        worksheet = get_worksheet(spreadsheet_id, worksheet_name)
        if not worksheet:
            return []
        
        all_records = worksheet.get_all_records()
        filtered_reports = []
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        for record in all_records:
            try:
                date_str = record.get('Shartnoma imzolangan sana', '').strip()
                if date_str:
                    if ' ' in date_str:
                        date_str = date_str.split(' ')[0]
                    
                    record_date = datetime.strptime(date_str, '%d.%m.%Y')
                    if start_dt <= record_date <= end_dt:
                        filtered_reports.append(record)
            
            except ValueError:
                continue
        
        logging.info(f"📅 Sana oralig'ida {len(filtered_reports)} ta hisobot topildi")
        return filtered_reports
    
    except Exception as e:
        logging.error(f"❌ Sana bo'yicha filtrlashda xato: {e}")
        return []


def get_seller_reports(spreadsheet_id: str, worksheet_name: str, seller_name: str) -> List[Dict]:
    """Sotuvchi bo'yicha hisobotlarni olish"""
    try:
        worksheet = get_worksheet(spreadsheet_id, worksheet_name)
        if not worksheet:
            return []
        
        all_records = worksheet.get_all_records()
        seller_reports = []
        
        for record in all_records:
            record_seller = record.get('Sotuvchi ismi', '').strip()
            if record_seller.lower() == seller_name.lower():
                seller_reports.append(record)
        
        logging.info(f"👤 Sotuvchi '{seller_name}' uchun {len(seller_reports)} ta hisobot topildi")
        return seller_reports
    
    except Exception as e:
        logging.error(f"❌ Sotuvchi hisobotlarini olishda xato: {e}")
        return []


def update_contract_amount(spreadsheet_id: str, worksheet_name: str, contract_id: str, amount: str) -> bool:
    """Shartnoma summasini yangilash"""
    try:
        worksheet = get_worksheet(spreadsheet_id, worksheet_name)
        if not worksheet:
            return False
        
        all_values = worksheet.get_all_values()
        
        if len(all_values) <= 1:
            return False
        
        headers = all_values[0]
        contract_col = None
        amount_col = None
        
        for i, header in enumerate(headers):
            if 'Shartnoma raqami' in header:
                contract_col = i
            elif 'Shartnoma summasi' in header:
                amount_col = i
        
        if contract_col is None or amount_col is None:
            logging.error("❌ Kerakli ustunlar topilmadi")
            return False
        
        for row_idx, row in enumerate(all_values[1:], start=2):
            if len(row) > contract_col and row[contract_col] == contract_id:
                cell_address = f"{chr(65 + amount_col)}{row_idx}"
                worksheet.update(cell_address, amount)
                
                logging.info(f"💰 Shartnoma {contract_id} uchun summa '{amount}' ga yangilandi")
                return True
        
        logging.warning(f"⚠️ Shartnoma ID {contract_id} topilmadi")
        return False
    
    except Exception as e:
        logging.error(f"❌ Summa yangilashda xato: {e}")
        return False


def clear_test_data(spreadsheet_id: str, worksheet_name: str) -> bool:
    """Test ma'lumotlarini tozalash"""
    try:
        worksheet = get_worksheet(spreadsheet_id, worksheet_name)
        if not worksheet:
            return False
        
        all_values = worksheet.get_all_values()
        
        if len(all_values) <= 1:
            return True
        
        rows_to_delete = []
        
        for row_idx, row in enumerate(all_values[1:], start=2):
            if len(row) >= len(COLUMN_HEADERS):
                is_test_row = any('TEST' in str(cell).upper() for cell in row)
                
                if is_test_row:
                    rows_to_delete.append(row_idx)
        
        for row_idx in reversed(rows_to_delete):
            worksheet.delete_rows(row_idx)
        
        if rows_to_delete:
            renumber_rows(worksheet)
        
        logging.info(f"🧹 {len(rows_to_delete)} ta test ma'lumoti tozalandi")
        return True
    
    except Exception as e:
        logging.error(f"❌ Test ma'lumotlarini tozalashda xato: {e}")
        return False


def renumber_rows(worksheet):
    """Qator raqamlarini qayta tartibga solish"""
    try:
        all_values = worksheet.get_all_values()
        
        if len(all_values) <= 1:
            return
        
        for i in range(1, len(all_values)):
            new_number = i
            cell_address = f"A{i + 1}"
            worksheet.update(cell_address, str(new_number))
        
        logging.info(f"🔢 {len(all_values) - 1} ta qatordagi raqamlar yangilandi")
    
    except Exception as e:
        logging.error(f"❌ Qator raqamlarini yangilashda xato: {e}")


def get_sheet_info(spreadsheet_id: str) -> Dict:
    """Sheet ma'lumotlarini olish"""
    try:
        client = get_google_sheets_client()
        if not client:
            return {}
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        info = {
            'title': spreadsheet.title,
            'id': spreadsheet.id,
            'url': spreadsheet.url,
            'worksheets': [],
            'daily_sheets': [],
            'links_count': get_links_count(spreadsheet_id),
            'last_updated': datetime.now().strftime('%d.%m.%Y %H:%M:%S')
        }
        
        for worksheet in spreadsheet.worksheets():
            all_values = worksheet.get_all_values()
            data_count = len(all_values) - 1 if all_values else 0
            
            worksheet_info = {
                'title': worksheet.title,
                'id': worksheet.id,
                'row_count': worksheet.row_count,
                'col_count': worksheet.col_count,
                'data_count': data_count
            }
            info['worksheets'].append(worksheet_info)
            
            if worksheet.title.startswith('SH ') or worksheet.title.startswith('VL '):
                sheet_type = "Toshkent shahar" if worksheet.title.startswith('SH ') else "Viloyat"
                info['daily_sheets'].append({
                    'title': worksheet.title,
                    'type': sheet_type,
                    'data_count': data_count
                })
        
        logging.info(f"📋 Sheet ma'lumotlari olindi: {info['title']} ({len(info['daily_sheets'])} kunlik sheet)")
        return info
    
    except Exception as e:
        logging.error(f"❌ Sheet ma'lumotlarini olishda xato: {e}")
        return {}


def handle_sheets_errors(func):
    """Google Sheets xatolarini boshqarish dekoratori"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            logging.error(f"❌ Google Sheets API xatosi: {e}")
            return None
        except gspread.exceptions.SpreadsheetNotFound:
            logging.error("❌ Spreadsheet topilmadi")
            return None
        except gspread.exceptions.WorksheetNotFound:
            logging.error("❌ Worksheet topilmadi")
            return None
        except Exception as e:
            logging.error(f"❌ Kutilmagan xato: {e}")
            return None
    
    return wrapper


# ==================== LOGGING SOZLAMALARI ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('google_sheets.log', encoding='utf-8')
    ]
)

logging.info("🚀 Google Sheets Integration moduli muvaffaqiyatli yuklandi")
logging.info("📊 YANGI: Kunlik sheetlar tizimi faollashtirildi")
logging.info("🏙️ Toshkent shahar: SH DD.MM.YYYY | Viloyat: VL DD.MM.YYYY")
logging.info("📋 Ustunlar: № | Mijoz | Telefon | Qo'shimcha Telefon | Mahsulot | Jo'natma | Dastavka | Izoh | Manzil | Sana | Yuborilgan | Shartnoma | Summa | Sotuvchi")
logging.info("🔗 YANGI: Linklar worksheet tizimi faollashtirildi")
logging.info("📊 YANGI: Kunlik ALL DATA worksheet tizimi faollashtirildi (ALL DATA DD.MM.YYYY)")