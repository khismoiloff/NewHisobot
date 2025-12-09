import sqlite3
import logging
from datetime import datetime, date

DB_NAME = 'bot_data.db'

def init_db():
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	
	cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_blocked INTEGER DEFAULT 0,
            assigned_group_id INTEGER,
            FOREIGN KEY (assigned_group_id) REFERENCES telegram_groups (group_id)
        )
    ''')
	
	try:
		cursor.execute("ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0")
		logging.info("Added is_blocked column to users table")
	except sqlite3.OperationalError:
		pass
	
	try:
		cursor.execute("ALTER TABLE users ADD COLUMN assigned_group_id INTEGER")
		logging.info("Added assigned_group_id column to users table")
	except sqlite3.OperationalError:
		pass
	
	cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_telegram_id INTEGER NOT NULL,
            client_name TEXT,
            phone_number TEXT,
            additional_phone_number TEXT,
            contract_id TEXT,
            contract_amount TEXT,
            product_type TEXT,
            client_location TEXT,
            product_image_id TEXT,
            submission_date DATE NOT NULL,
            submission_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            confirmed_by_helper_id INTEGER,
            confirmation_timestamp TIMESTAMP,
            group_message_id INTEGER,
            google_sheet_id INTEGER,
            is_tashkent INTEGER DEFAULT 0,
            FOREIGN KEY (user_telegram_id) REFERENCES users (telegram_id),
            FOREIGN KEY (google_sheet_id) REFERENCES google_sheets (id)
        )
    ''')
	
	try:
		cursor.execute("ALTER TABLE sales_reports ADD COLUMN google_sheet_id INTEGER")
		logging.info("Added google_sheet_id column to sales_reports table")
	except sqlite3.OperationalError:
		pass
	
	try:
		cursor.execute("ALTER TABLE sales_reports ADD COLUMN contract_amount TEXT")
		logging.info("Added contract_amount column to sales_reports table")
	except sqlite3.OperationalError:
		pass
	
	try:
		cursor.execute("ALTER TABLE sales_reports ADD COLUMN is_tashkent INTEGER DEFAULT 0")
		logging.info("Added is_tashkent column to sales_reports table")
	except sqlite3.OperationalError:
		pass
	
	cursor.execute('''
        CREATE TABLE IF NOT EXISTS telegram_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER UNIQUE NOT NULL,
            group_name TEXT NOT NULL,
            message_thread_id INTEGER,
            google_sheet_id INTEGER,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (google_sheet_id) REFERENCES google_sheets (id)
        )
    ''')
	
	try:
		cursor.execute("ALTER TABLE telegram_groups ADD COLUMN google_sheet_id INTEGER")
		logging.info("Added google_sheet_id column to telegram_groups table")
	except sqlite3.OperationalError:
		pass
	
	cursor.execute('''
        CREATE TABLE IF NOT EXISTS google_sheets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sheet_name TEXT NOT NULL,
            spreadsheet_id TEXT UNIQUE NOT NULL,
            worksheet_name TEXT NOT NULL DEFAULT 'Sheet1',
            is_active INTEGER DEFAULT 1,
            added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
	
	try:
		cursor.execute("ALTER TABLE google_sheets ADD COLUMN sheet_name TEXT")
		logging.info("Added sheet_name column to google_sheets table")
	except sqlite3.OperationalError:
		pass
	
	try:
		cursor.execute("ALTER TABLE google_sheets ADD COLUMN is_active INTEGER DEFAULT 1")
		logging.info("Added is_active column to google_sheets table")
	except sqlite3.OperationalError:
		pass
	
	cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT UNIQUE NOT NULL,
            setting_value TEXT NOT NULL,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
	
	cursor.execute("INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES ('admin_password', '2025')")
	
	conn.commit()
	conn.close()
	logging.info(f"Database '{DB_NAME}' initialized successfully with all tables (including is_tashkent).")

async def add_user_to_db(telegram_id: int, full_name: str, assigned_group_id: int = None):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute(
			"INSERT INTO users (telegram_id, full_name, assigned_group_id) VALUES (?, ?, ?)",
			(telegram_id, full_name, assigned_group_id)
		)
		conn.commit()
		logging.info(f"User {telegram_id} added to database with group {assigned_group_id}.")
	except sqlite3.IntegrityError:
		logging.warning(f"User {telegram_id} already exists in database.")
	finally:
		conn.close()

async def check_user_exists(telegram_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
	result = cursor.fetchone()
	conn.close()
	return result is not None

async def check_user_blocked(telegram_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT is_blocked FROM users WHERE telegram_id = ?", (telegram_id,))
		result = cursor.fetchone()
		return bool(result[0]) if result else False
	except Exception as e:
		logging.error(f"Error checking user blocked status: {e}")
		return False
	finally:
		conn.close()

async def get_user_assigned_group(telegram_id: int) -> tuple | None:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("""
            SELECT tg.group_id, tg.group_name, tg.message_thread_id, tg.google_sheet_id
            FROM users u
            JOIN telegram_groups tg ON u.assigned_group_id = tg.group_id
            WHERE u.telegram_id = ?
        """, (telegram_id,))
		result = cursor.fetchone()
		return result
	except Exception as e:
		logging.error(f"Error getting user assigned group: {e}")
		return None
	finally:
		conn.close()

async def block_user(telegram_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("UPDATE users SET is_blocked = 1 WHERE telegram_id = ?", (telegram_id,))
		updated = cursor.rowcount > 0
		conn.commit()
		if updated:
			logging.info(f"User {telegram_id} blocked successfully.")
		return updated
	except Exception as e:
		logging.error(f"Error blocking user {telegram_id}: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def unblock_user(telegram_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("UPDATE users SET is_blocked = 0 WHERE telegram_id = ?", (telegram_id,))
		updated = cursor.rowcount > 0
		conn.commit()
		if updated:
			logging.info(f"User {telegram_id} unblocked successfully.")
		return updated
	except Exception as e:
		logging.error(f"Error unblocking user {telegram_id}: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def get_users_paginated(page: int = 1, per_page: int = 10) -> tuple:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT COUNT(*) FROM users")
		total_count = cursor.fetchone()[0]
		
		offset = (page - 1) * per_page
		cursor.execute("""
            SELECT u.id, u.telegram_id, u.full_name, u.registration_date,
                   COALESCE(u.is_blocked, 0) as is_blocked,
                   COALESCE(tg.group_name, 'Guruh tayinlanmagan') as group_name
            FROM users u
            LEFT JOIN telegram_groups tg ON u.assigned_group_id = tg.group_id
            ORDER BY u.registration_date DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
		users = cursor.fetchall()
		
		total_pages = (total_count + per_page - 1) // per_page
		return users, total_pages, total_count
	except Exception as e:
		logging.error(f"Error fetching paginated users: {e}")
		return [], 0, 0
	finally:
		conn.close()

async def check_full_name_exists(full_name: str) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT 1 FROM users WHERE LOWER(full_name) = LOWER(?)", (full_name,))
		result = cursor.fetchone()
		return result is not None
	except Exception as e:
		logging.error(f"Error checking full name existence: {e}")
		return False
	finally:
		conn.close()

async def get_user_reports_count(telegram_id: int) -> int:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT COUNT(*) FROM sales_reports WHERE user_telegram_id = ?", (telegram_id,))
		result = cursor.fetchone()
		return result[0] if result else 0
	except Exception as e:
		logging.error(f"Error getting user reports count: {e}")
		return 0
	finally:
		conn.close()

async def add_sales_report(user_id: int, report_data: dict, group_msg_id: int = None, google_sheet_id: int = None):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		# is_tashkent ustunini tekshirish va qo'shish
		try:
			cursor.execute("ALTER TABLE sales_reports ADD COLUMN is_tashkent INTEGER DEFAULT 0")
			logging.info("Added is_tashkent column to sales_reports table")
		except sqlite3.OperationalError:
			pass
		
		# is_tashkent qiymatini olish
		is_tashkent = 1 if report_data.get('is_tashkent', False) else 0
		
		cursor.execute("""
            INSERT INTO sales_reports (
                user_telegram_id, client_name, phone_number, additional_phone_number,
                contract_id, contract_amount, product_type, client_location, product_image_id,
                submission_date, group_message_id, google_sheet_id, is_tashkent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
			user_id,
			report_data.get('client_name'),
			report_data.get('phone_number'),
			report_data.get('additional_phone_number', 'Mavjud emas'),
			report_data.get('contract_id'),
			report_data.get('contract_amount'),
			report_data.get('product_type'),
			report_data.get('client_location'),
			report_data.get('product_image_id'),
			date.today(),
			group_msg_id,
			google_sheet_id,
			is_tashkent
		))
		conn.commit()
		logging.info(f"Sales report for user {user_id} added to database (is_tashkent={is_tashkent}).")
		return cursor.lastrowid
	except Exception as e:
		logging.error(f"Error adding sales report to DB: {e}")
		return None
	finally:
		conn.close()

async def get_todays_sales_by_user(user_telegram_id: int) -> list:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	today_str = date.today().isoformat()
	try:
		cursor.execute(
			"SELECT contract_id, product_type FROM sales_reports WHERE user_telegram_id = ? AND submission_date = ?",
			(user_telegram_id, today_str)
		)
		sales = cursor.fetchall()
		return sales
	except Exception as e:
		logging.error(f"Error fetching today's sales for user {user_telegram_id}: {e}")
		return []
	finally:
		conn.close()

async def update_report_status_in_db(group_message_id: int, status: str, helper_id: int = None):
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("""
            UPDATE sales_reports
            SET status = ?, confirmed_by_helper_id = ?, confirmation_timestamp = ?
            WHERE group_message_id = ?
        """, (status, helper_id, datetime.now(), group_message_id))
		conn.commit()
		if cursor.rowcount > 0:
			logging.info(f"Report status updated to '{status}' for group_message_id {group_message_id}.")
			return True
		else:
			logging.warning(f"No report found to update status for group_message_id {group_message_id}.")
			return False
	except Exception as e:
		logging.error(f"Error updating report status in DB: {e}")
		return False
	finally:
		conn.close()

async def get_all_users() -> list:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute(
			"SELECT id, telegram_id, full_name, registration_date FROM users ORDER BY registration_date DESC")
		users = cursor.fetchall()
		return users
	except Exception as e:
		logging.error(f"Error fetching all users: {e}")
		return []
	finally:
		conn.close()

async def delete_user_from_db(telegram_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("DELETE FROM sales_reports WHERE user_telegram_id = ?", (telegram_id,))
		reports_deleted = cursor.rowcount
		logging.info(f"{reports_deleted} reports deleted for user {telegram_id}.")
		
		cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
		user_deleted = cursor.rowcount > 0
		conn.commit()
		if user_deleted:
			logging.info(f"User {telegram_id} deleted from database.")
		return user_deleted
	except Exception as e:
		logging.error(f"Error deleting user {telegram_id} from DB: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def get_all_sales_reports() -> list:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT * FROM sales_reports ORDER BY submission_timestamp DESC")
		reports = cursor.fetchall()
		return reports
	except Exception as e:
		logging.error(f"Error fetching all sales reports: {e}")
		return []
	finally:
		conn.close()

async def delete_sales_report(report_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("DELETE FROM sales_reports WHERE id = ?", (report_id,))
		deleted = cursor.rowcount > 0
		conn.commit()
		if deleted:
			logging.info(f"Sales report {report_id} deleted from database.")
		return deleted
	except Exception as e:
		logging.error(f"Error deleting sales report {report_id} from DB: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def add_telegram_group(group_id: int, group_name: str, message_thread_id: int = None,
                             google_sheet_id: int = None) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute(
			"INSERT INTO telegram_groups (group_id, group_name, message_thread_id, google_sheet_id) VALUES (?, ?, ?, ?)",
			(group_id, group_name, message_thread_id, google_sheet_id)
		)
		conn.commit()
		logging.info(
			f"Group {group_name} ({group_id}) with topic {message_thread_id} and sheet {google_sheet_id} added to database.")
		return True
	except sqlite3.IntegrityError:
		logging.warning(f"Group {group_id} already exists in database.")
		return False
	except Exception as e:
		logging.error(f"Error adding telegram group to DB: {e}")
		return False
	finally:
		conn.close()

async def get_all_telegram_groups() -> list:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("""
            SELECT tg.id, tg.group_id, tg.group_name, tg.message_thread_id, tg.google_sheet_id,
                   COALESCE(gs.sheet_name, 'Sheet tayinlanmagan') as sheet_name
            FROM telegram_groups tg
            LEFT JOIN google_sheets gs ON tg.google_sheet_id = gs.id
            ORDER BY tg.group_name ASC
        """)
		groups = cursor.fetchall()
		return groups
	except Exception as e:
		logging.error(f"Error fetching all telegram groups: {e}")
		return []
	finally:
		conn.close()

async def get_telegram_group_by_id(group_id: int) -> tuple | None:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("""
            SELECT tg.id, tg.group_id, tg.group_name, tg.message_thread_id, tg.google_sheet_id,
                   COALESCE(gs.sheet_name, 'Sheet tayinlanmagan') as sheet_name
            FROM telegram_groups tg
            LEFT JOIN google_sheets gs ON tg.google_sheet_id = gs.id
            WHERE tg.group_id = ?
        """, (group_id,))
		result = cursor.fetchone()
		return result
	except Exception as e:
		logging.error(f"Error fetching telegram group by id {group_id}: {e}")
		return None
	finally:
		conn.close()

async def delete_telegram_group(group_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("UPDATE users SET assigned_group_id = NULL WHERE assigned_group_id = ?", (group_id,))
		cursor.execute("DELETE FROM telegram_groups WHERE group_id = ?", (group_id,))
		deleted = cursor.rowcount > 0
		conn.commit()
		if deleted:
			logging.info(f"Group {group_id} deleted from database.")
		return deleted
	except Exception as e:
		logging.error(f"Error deleting telegram group {group_id} from DB: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def add_google_sheet(sheet_name: str, spreadsheet_id: str, worksheet_name: str = 'Sheet1') -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute(
			"INSERT INTO google_sheets (sheet_name, spreadsheet_id, worksheet_name) VALUES (?, ?, ?)",
			(sheet_name, spreadsheet_id, worksheet_name)
		)
		conn.commit()
		logging.info(f"Google Sheet added: {sheet_name} - ID={spreadsheet_id}, Worksheet={worksheet_name}")
		return True
	except sqlite3.IntegrityError:
		logging.warning(f"Google Sheet with spreadsheet_id {spreadsheet_id} already exists.")
		return False
	except Exception as e:
		logging.error(f"Error adding Google Sheet to DB: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def get_all_google_sheets() -> list:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute(
			"SELECT id, sheet_name, spreadsheet_id, worksheet_name, is_active FROM google_sheets WHERE is_active = 1 ORDER BY sheet_name ASC")
		sheets = cursor.fetchall()
		return sheets
	except Exception as e:
		logging.error(f"Error fetching Google Sheets: {e}")
		return []
	finally:
		conn.close()

async def get_google_sheet_by_id(sheet_id: int) -> tuple | None:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute(
			"SELECT id, sheet_name, spreadsheet_id, worksheet_name, is_active FROM google_sheets WHERE id = ?",
			(sheet_id,))
		result = cursor.fetchone()
		return result
	except Exception as e:
		logging.error(f"Error fetching Google Sheet by id {sheet_id}: {e}")
		return None
	finally:
		conn.close()

async def delete_google_sheet(sheet_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("UPDATE telegram_groups SET google_sheet_id = NULL WHERE google_sheet_id = ?", (sheet_id,))
		cursor.execute("UPDATE google_sheets SET is_active = 0 WHERE id = ?", (sheet_id,))
		updated = cursor.rowcount > 0
		conn.commit()
		if updated:
			logging.info(f"Google Sheet {sheet_id} deactivated.")
		return updated
	except Exception as e:
		logging.error(f"Error deleting Google Sheet {sheet_id} from DB: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def get_user_by_telegram_id(telegram_id: int) -> tuple | None:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("""
            SELECT u.id, u.telegram_id, u.full_name, u.registration_date,
                   COALESCE(u.is_blocked, 0) as is_blocked,
                   COALESCE(tg.group_name, 'Guruh tayinlanmagan') as group_name
            FROM users u
            LEFT JOIN telegram_groups tg ON u.assigned_group_id = tg.group_id
            WHERE u.telegram_id = ?
        """, (telegram_id,))
		result = cursor.fetchone()
		return result
	except Exception as e:
		logging.error(f"Error fetching user by telegram_id {telegram_id}: {e}")
		return None
	finally:
		conn.close()

async def get_reports_by_user(telegram_id: int, limit: int = None) -> list:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		if limit:
			cursor.execute("""
                SELECT * FROM sales_reports
                WHERE user_telegram_id = ?
                ORDER BY submission_timestamp DESC
                LIMIT ?
            """, (telegram_id, limit))
		else:
			cursor.execute("""
                SELECT * FROM sales_reports
                WHERE user_telegram_id = ?
                ORDER BY submission_timestamp DESC
            """, (telegram_id,))
		reports = cursor.fetchall()
		return reports
	except Exception as e:
		logging.error(f"Error fetching reports for user {telegram_id}: {e}")
		return []
	finally:
		conn.close()

async def get_reports_by_status(status: str) -> list:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT * FROM sales_reports WHERE status = ? ORDER BY submission_timestamp DESC", (status,))
		reports = cursor.fetchall()
		return reports
	except Exception as e:
		logging.error(f"Error fetching reports by status {status}: {e}")
		return []
	finally:
		conn.close()

async def get_group_google_sheet(group_id: int) -> tuple | None:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("""
            SELECT gs.id, gs.sheet_name, gs.spreadsheet_id, gs.worksheet_name, gs.is_active
            FROM telegram_groups tg
            JOIN google_sheets gs ON tg.google_sheet_id = gs.id
            WHERE tg.group_id = ? AND gs.is_active = 1
        """, (group_id,))
		result = cursor.fetchone()
		return result
	except Exception as e:
		logging.error(f"Error fetching Google Sheet for group {group_id}: {e}")
		return None
	finally:
		conn.close()

async def update_user_name(telegram_id: int, new_name: str) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("UPDATE users SET full_name = ? WHERE telegram_id = ?", (new_name, telegram_id))
		updated = cursor.rowcount > 0
		conn.commit()
		if updated:
			logging.info(f"User {telegram_id} name updated to '{new_name}'.")
		return updated
	except Exception as e:
		logging.error(f"Error updating user name for {telegram_id}: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def update_user_group(telegram_id: int, group_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("UPDATE users SET assigned_group_id = ? WHERE telegram_id = ?", (group_id, telegram_id))
		updated = cursor.rowcount > 0
		conn.commit()
		if updated:
			logging.info(f"User {telegram_id} group updated to {group_id}.")
		return updated
	except Exception as e:
		logging.error(f"Error updating user group for {telegram_id}: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def update_group_google_sheet(group_id: int, sheet_id: int) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("UPDATE telegram_groups SET google_sheet_id = ? WHERE group_id = ?", (sheet_id, group_id))
		updated = cursor.rowcount > 0
		conn.commit()
		if updated:
			logging.info(f"Group {group_id} Google Sheet updated to {sheet_id}.")
		return updated
	except Exception as e:
		logging.error(f"Error updating group Google Sheet for {group_id}: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def get_database_stats() -> dict:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		stats = {}
		
		# Jami foydalanuvchilar
		cursor.execute("SELECT COUNT(*) FROM users")
		stats['total_users'] = cursor.fetchone()[0]
		
		# Jami hisobotlar
		cursor.execute("SELECT COUNT(*) FROM sales_reports")
		stats['total_reports'] = cursor.fetchone()[0]
		
		# Tasdiqlangan hisobotlar
		cursor.execute("SELECT COUNT(*) FROM sales_reports WHERE status = 'confirmed'")
		stats['confirmed_reports'] = cursor.fetchone()[0]
		
		# Kutilayotgan hisobotlar
		cursor.execute("SELECT COUNT(*) FROM sales_reports WHERE status = 'pending'")
		stats['pending_reports'] = cursor.fetchone()[0]
		
		# Bugungi hisobotlar
		today_str = date.today().isoformat()
		cursor.execute("SELECT COUNT(*) FROM sales_reports WHERE submission_date = ?", (today_str,))
		stats['today_reports'] = cursor.fetchone()[0]
		
		cursor.execute("SELECT COUNT(*) FROM sales_reports WHERE is_tashkent = 1")
		stats['tashkent_reports'] = cursor.fetchone()[0]
		
		cursor.execute("SELECT COUNT(*) FROM sales_reports WHERE is_tashkent = 0 OR is_tashkent IS NULL")
		stats['other_reports'] = cursor.fetchone()[0]
		
		# Tasdiqlash foizi
		if stats['total_reports'] > 0:
			stats['confirmation_rate'] = round((stats['confirmed_reports'] / stats['total_reports']) * 100, 1)
		else:
			stats['confirmation_rate'] = 0
		
		return stats
	except Exception as e:
		logging.error(f"Error getting database stats: {e}")
		return {}
	finally:
		conn.close()

async def get_reports_count_by_date(start_date: str, end_date: str) -> int:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("""
            SELECT COUNT(*) FROM sales_reports
            WHERE submission_date BETWEEN ? AND ?
        """, (start_date, end_date))
		result = cursor.fetchone()
		return result[0] if result else 0
	except Exception as e:
		logging.error(f"Error getting reports count by date range: {e}")
		return 0
	finally:
		conn.close()

async def get_total_users_count() -> int:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT COUNT(*) FROM users")
		result = cursor.fetchone()
		return result[0] if result else 0
	except Exception as e:
		logging.error(f"Error getting total users count: {e}")
		return 0
	finally:
		conn.close()

async def get_total_reports_count() -> int:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT COUNT(*) FROM sales_reports")
		result = cursor.fetchone()
		return result[0] if result else 0
	except Exception as e:
		logging.error(f"Error getting total reports count: {e}")
		return 0
	finally:
		conn.close()

async def get_confirmed_reports_count() -> int:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT COUNT(*) FROM sales_reports WHERE status = 'confirmed'")
		result = cursor.fetchone()
		return result[0] if result else 0
	except Exception as e:
		logging.error(f"Error getting confirmed reports count: {e}")
		return 0
	finally:
		conn.close()

async def get_pending_reports_count() -> int:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT COUNT(*) FROM sales_reports WHERE status = 'pending'")
		result = cursor.fetchone()
		return result[0] if result else 0
	except Exception as e:
		logging.error(f"Error getting pending reports count: {e}")
		return 0
	finally:
		conn.close()

async def get_current_password() -> str:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("SELECT setting_value FROM bot_settings WHERE setting_key = 'admin_password'")
		result = cursor.fetchone()
		return result[0] if result else "2025"
	except Exception as e:
		logging.error(f"Error getting current password: {e}")
		return "2025"
	finally:
		conn.close()

async def update_password(new_password: str) -> bool:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		cursor.execute("""
            UPDATE bot_settings SET setting_value = ?, updated_date = ?
            WHERE setting_key = 'admin_password'
        """, (new_password, datetime.now()))
		updated = cursor.rowcount > 0
		conn.commit()
		if updated:
			logging.info(f"Password updated successfully.")
		return updated
	except Exception as e:
		logging.error(f"Error updating password: {e}")
		conn.rollback()
		return False
	finally:
		conn.close()

async def get_tashkent_reports(limit: int = None) -> list:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		if limit:
			cursor.execute("""
                SELECT * FROM sales_reports
                WHERE is_tashkent = 1
                ORDER BY submission_timestamp DESC
                LIMIT ?
            """, (limit,))
		else:
			cursor.execute("""
                SELECT * FROM sales_reports
                WHERE is_tashkent = 1
                ORDER BY submission_timestamp DESC
            """)
		reports = cursor.fetchall()
		return reports
	except Exception as e:
		logging.error(f"Error fetching Tashkent reports: {e}")
		return []
	finally:
		conn.close()

async def get_viloyat_reports(limit: int = None) -> list:
	conn = sqlite3.connect(DB_NAME)
	cursor = conn.cursor()
	try:
		if limit:
			cursor.execute("""
                SELECT * FROM sales_reports
                WHERE is_tashkent = 0 OR is_tashkent IS NULL
                ORDER BY submission_timestamp DESC
                LIMIT ?
            """, (limit,))
		else:
			cursor.execute("""
                SELECT * FROM sales_reports
                WHERE is_tashkent = 0 OR is_tashkent IS NULL
                ORDER BY submission_timestamp DESC
            """)
		reports = cursor.fetchall()
		return reports
	except Exception as e:
		logging.error(f"Error fetching Viloyat reports: {e}")
		return []
	finally:
		conn.close()
