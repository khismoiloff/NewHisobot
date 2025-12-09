from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from config import DEVELOPER_USERNAME, DEVELOPER_USER_ID

def get_main_menu_reply_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="📝 Hisobot topshirish")],
        [KeyboardButton(text="📊 Sotuvlarim"), KeyboardButton(text="👨‍💻 Dasturchi")]
    ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="👇 Kerakli bo'limni tanlang"
    )
    return keyboard

def get_developer_contact_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="👨‍💻 Dasturchi bilan bog'lanish",
                url=f"tg://user?id={DEVELOPER_USER_ID}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_yes_no_additional_phone_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="add_phone_yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="add_phone_no")
        ],
        [InlineKeyboardButton(text="🚫 Jarayonni bekor qilish", callback_data="cancel_report_submission")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_report_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🚫 Jarayonni bekor qilish", callback_data="cancel_report_submission")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_report_confirmation_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_report"),
            InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="edit_report")
        ],
        [
            InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="cancel_report")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_report_confirmed_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ Tasdiqlandi", callback_data="status_confirmed_noop")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_menu_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="👥 Ishchilar", callback_data="admin_workers"),
            InlineKeyboardButton(text="📊 Hisobotlar", callback_data="admin_reports")
        ],
        [
            InlineKeyboardButton(text="🏢 Guruhlar", callback_data="admin_groups"),
            InlineKeyboardButton(text="📈 Google Sheets", callback_data="admin_sheets")
        ],
        [
            InlineKeyboardButton(text="🔐 Parolni o'zgartirish", callback_data="admin_change_password"),
            InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin_settings")
        ],
        [
            InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="admin_exit")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_cancel_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="cancel_admin_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_workers_list_keyboard(workers: list, page: int = 1) -> InlineKeyboardMarkup:
    buttons = []
    
    number_buttons = []
    for i, worker in enumerate(workers, 1):
        user_id, telegram_id, full_name, reg_date, is_blocked, group_name = worker
        number_buttons.append(InlineKeyboardButton(
            text=str(i),
            callback_data=f"worker_select_{telegram_id}"
        ))
    
    for i in range(0, len(number_buttons), 5):
        buttons.append(number_buttons[i:i + 5])
    
    buttons.append([InlineKeyboardButton(text="🔙 Admin menyu", callback_data="admin_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_worker_management_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📊 Sotuvlarini ko'rish", callback_data=f"worker_sales_{telegram_id}"),
            InlineKeyboardButton(text="🔒 Bloklash/Ochish", callback_data=f"worker_block_{telegram_id}")
        ],
        [
            InlineKeyboardButton(text="👥 Guruhini o'zgartirish", callback_data=f"worker_group_{telegram_id}"),
            InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"worker_delete_{telegram_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Ishchilar", callback_data="admin_workers")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_groups_list_keyboard(groups: list) -> InlineKeyboardMarkup:
    buttons = []
    
    for group in groups:
        db_id, group_id, group_name, topic_id, google_sheet_id, sheet_name = group
        sheet_info = f" ({sheet_name})" if sheet_name != 'Sheet tayinlanmagan' else ""
        buttons.append([InlineKeyboardButton(
            text=f"📁 {group_name}{sheet_info}",
            callback_data=f"group_select_{group_id}"
        )])
    
    buttons.append([
        InlineKeyboardButton(text="➕ Guruh qo'shish", callback_data="group_add"),
        InlineKeyboardButton(text="🗑️ Guruh o'chirish", callback_data="group_delete")
    ])
    buttons.append([InlineKeyboardButton(text="🔙 Admin menyu", callback_data="admin_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_worker_groups_keyboard(groups: list, worker_telegram_id: int) -> InlineKeyboardMarkup:
    buttons = []
    
    for group in groups:
        db_id, group_id, group_name, topic_id, google_sheet_id, sheet_name = group
        sheet_info = f" ({sheet_name})" if sheet_name != 'Sheet tayinlanmagan' else ""
        buttons.append([InlineKeyboardButton(
            text=f"📁 {group_name}{sheet_info}",
            callback_data=f"assign_worker_{worker_telegram_id}_{group_id}"
        )])
    
    buttons.append(
        [InlineKeyboardButton(text="🔙 Ishchi boshqaruvi", callback_data=f"worker_select_{worker_telegram_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_google_sheets_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📋 Barcha Sheetlar", callback_data="sheets_list"),
            InlineKeyboardButton(text="➕ Sheet qo'shish", callback_data="sheets_add")
        ],
        [
            InlineKeyboardButton(text="🧪 Test qilish", callback_data="sheets_test_menu"),
            InlineKeyboardButton(text="📊 Statistika", callback_data="sheets_stats")
        ],
        [
            InlineKeyboardButton(text="🔙 Admin menyu", callback_data="admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_sheets_list_keyboard(sheets: list) -> InlineKeyboardMarkup:
    buttons = []
    
    for sheet in sheets:
        sheet_id, sheet_name, spreadsheet_id, worksheet_name, is_active = sheet
        buttons.append([InlineKeyboardButton(
            text=f"📊 {sheet_name}",
            callback_data=f"sheet_select_{sheet_id}"
        )])
    
    buttons.append([
        InlineKeyboardButton(text="➕ Yangi Sheet", callback_data="sheets_add"),
        InlineKeyboardButton(text="🔙 Google Sheets", callback_data="admin_sheets")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_sheet_management_keyboard(sheet_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🧪 Test qilish", callback_data=f"sheet_test_{sheet_id}"),
            InlineKeyboardButton(text="📊 Statistika", callback_data=f"sheet_stats_{sheet_id}")
        ],
        [
            InlineKeyboardButton(text="🗑️ O'chirish", callback_data=f"sheet_delete_{sheet_id}"),
            InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"sheet_update_{sheet_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Sheetlar ro'yxati", callback_data="sheets_list")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_google_sheets_selection_keyboard(sheets: list) -> InlineKeyboardMarkup:
    buttons = []
    
    for sheet in sheets:
        sheet_id, sheet_name, spreadsheet_id, worksheet_name, is_active = sheet
        buttons.append([InlineKeyboardButton(
            text=f"📊 {sheet_name}",
            callback_data=f"select_sheet_{sheet_id}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="cancel_admin_action")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_group_selection_keyboard(groups: list) -> InlineKeyboardMarkup:
    buttons = []
    for db_id, group_id, group_name, message_thread_id, google_sheet_id, sheet_name in groups:
        sheet_info = f" ({sheet_name})" if sheet_name != 'Sheet tayinlanmagan' else ""
        buttons.append([InlineKeyboardButton(
            text=f"📁 {group_name}{sheet_info}",
            callback_data=f"select_registration_group_{group_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_dynamic_group_selection_inline_keyboard(groups: list) -> InlineKeyboardMarkup:
    buttons = []
    for db_id, group_id, group_name, message_thread_id, google_sheet_id, sheet_name in groups:
        callback_data_value = f"select_group_{group_id}_{message_thread_id if message_thread_id is not None else '0'}"
        sheet_info = f" ({sheet_name})" if sheet_name != 'Sheet tayinlanmagan' else ""
        buttons.append([InlineKeyboardButton(
            text=f"{group_name}{sheet_info} (Mavzu ID: {message_thread_id if message_thread_id is not None else 'Yo\'q'})",
            callback_data=callback_data_value
        )])
    buttons.append([InlineKeyboardButton(text="🚫 Jarayonni bekor qilish", callback_data="cancel_report_submission")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_reports_stats_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="📅 Oylik hisobot", callback_data="reports_monthly"),
            InlineKeyboardButton(text="👥 Sotuvchilar", callback_data="reports_sellers")
        ],
        [
            InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="reports_general"),
            InlineKeyboardButton(text="📈 Google Sheets", callback_data="reports_sheets")
        ],
        [
            InlineKeyboardButton(text="🔙 Admin menyu", callback_data="admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_worker_sales_back_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔙 Ishchi ma'lumotlari", callback_data=f"worker_select_{telegram_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_password_change_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🔐 Parolni o'zgartirish", callback_data="change_password_start"),
            InlineKeyboardButton(text="👁️ Joriy parolni ko'rish", callback_data="view_current_password")
        ],
        [
            InlineKeyboardButton(text="🔙 Admin menyu", callback_data="admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_settings_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🔐 Parol sozlamalari", callback_data="admin_change_password"),
            InlineKeyboardButton(text="📊 Tizim ma'lumotlari", callback_data="system_info")
        ],
        [
            InlineKeyboardButton(text="🗄️ Ma'lumotlar bazasi", callback_data="database_info"),
            InlineKeyboardButton(text="📈 Umumiy statistika", callback_data="reports_general")
        ],
        [
            InlineKeyboardButton(text="🔙 Admin menyu", callback_data="admin_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_edit_selection_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="👤 Mijoz ismi", callback_data="edit_client_name"),
            InlineKeyboardButton(text="📱 Telefon", callback_data="edit_phone")
        ],
        [
            InlineKeyboardButton(text="📱 Qo'shimcha telefon", callback_data="edit_additional_phone"),
            InlineKeyboardButton(text="🛍️ Mahsulot", callback_data="edit_product")
        ],
        [
            InlineKeyboardButton(text="📍 Manzil", callback_data="edit_location"),
            InlineKeyboardButton(text="📄 Shartnoma ID", callback_data="edit_contract_id")
        ],
        [
            InlineKeyboardButton(text="💰 Summa", callback_data="edit_contract_amount"),
            InlineKeyboardButton(text="🖼️ Rasm", callback_data="edit_image")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_confirmation")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_group_report_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_report_action"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="reject_report_action")
        ],
        # [
        #     InlineKeyboardButton(text="👨‍💼 Sotuvchi", callback_data="view_seller_info")
        # ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_rejection_reason_keyboard(helper_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="📞 Sababi haqida so'rash",
                callback_data=f"contact_helper_{helper_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_contact_helper_keyboard(helper_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="💬 Helper bilan bog'lanish",
                url=f"tg://user?id={helper_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_view_seller_keyboard(seller_telegram_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(
                text="👨‍💼 Sotuvchi bilan bog'lanish",
                url=f"tg://user?id={seller_telegram_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_region_selection_keyboard() -> InlineKeyboardMarkup:
    """
    O'zbekiston viloyatlari va Toshkent shahar tanlash klaviaturasi
    """
    regions = [
        "Toshkent shahar", "Toshkent viloyati", "Andijon", "Buxoro", 
        "Farg'ona", "Jizzax", "Xorazm", "Namangan", "Navoiy", 
        "Qashqadaryo", "Qoraqalpog'iston", "Samarqand", "Sirdaryo", "Surxondaryo"
    ]
    
    buttons = []
    # Har qatorda 2 ta tugma
    for i in range(0, len(regions), 2):
        row = []
        row.append(InlineKeyboardButton(
            text=regions[i],
            callback_data=f"select_region_{regions[i]}"
        ))
        if i + 1 < len(regions):
            row.append(InlineKeyboardButton(
                text=regions[i + 1],
                callback_data=f"select_region_{regions[i + 1]}"
            ))
        buttons.append(row)
    
    # Bekor qilish tugmasi
    buttons.append([InlineKeyboardButton(text="🚫 Jarayonni bekor qilish", callback_data="cancel_report_submission")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)
