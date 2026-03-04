"""
ULTRA SIMPLE BRANVEE SIGNAL BOT - FIXED
"""

import logging
import sqlite3
import os
from datetime import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = "8741454658:AAGlyxcVQMH7tKd13OmM2Y2VGa9ex9LbPfo"
API_URL = "https://branvee-gold-system-production.up.railway.app"
DB_PATH = 'data/branvee.db'

# Your sticker IDs
STICKERS = {
    'BUY': 'CAACAgUAAxkBAAEQrM1pqHn0R0kEa_N26VvUd3ql5z2ALQAC8BAAAuyHeVQNfOSljHlxXToE',
    'SELL': 'CAACAgUAAxkBAAEQrM9pqHn3xrEok5y9PgRla3BDglVNRwACBBIAAyV4VL-svKl04_rUOgQ',
    'HOLD': 'CAACAgUAAxkBAAEQrNFpqHoAAYs3q4IclmTtzx1bM5jWTmMAAnMVAAJkTHlUfqdnK5jbckQ6BA'
}

# Database
os.makedirs('data', exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        token TEXT UNIQUE NOT NULL,
        telegram_id INTEGER,
        expires_at TEXT NOT NULL,
        is_suspended INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()
    print("✅ Database ready")

def get_user_by_email(email):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def update_telegram_id(user_id, telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET telegram_id = ? WHERE id = ?', (telegram_id, user_id))
    conn.commit()
    conn.close()

# ============================
# HANDLERS
# ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    keyboard = [
        [InlineKeyboardButton("🔐 LOGIN", callback_data='login')]
    ]
    await update.message.reply_text(
        "👋 Welcome to BRANVEE SIGNAL BOT!\n\nTap LOGIN to access:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'login':
        await query.edit_message_text(
            "📧 **LOGIN**\n\nPlease send your email in this format:\n`email: your@email.com`",
            parse_mode='Markdown'
        )
    
    elif query.data == 'main_menu':
        await show_main_menu(query, context)
    
    elif query.data == 'get_signal':
        await send_signal(query, context)
    
    elif query.data == 'account':
        await show_account(query, context)
    
    elif query.data == 'logout':
        context.user_data.clear()
        keyboard = [
            [InlineKeyboardButton("🔐 LOGIN", callback_data='login')]
        ]
        await query.edit_message_text(
            "✅ Logged out. Tap LOGIN to continue:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    text = update.message.text
    
    if text.startswith('email:'):
        email = text.replace('email:', '').strip()
        
        user = get_user_by_email(email)
        
        if not user:
            await update.message.reply_text("❌ Email not found in database")
            return
        
        if user['is_suspended']:
            await update.message.reply_text("❌ Account is suspended")
            return
        
        # Store user data
        context.user_data['user_id'] = user['id']
        context.user_data['email'] = user['email']
        context.user_data['expires_at'] = user['expires_at']
        
        await update.message.reply_text(
            f"✅ Email verified!\n\nNow send your token in this format:\n`token: {user['token']}`"
        )
    
    elif text.startswith('token:'):
        token = text.replace('token:', '').strip()
        user_id = context.user_data.get('user_id')
        
        if not user_id:
            await update.message.reply_text("❌ Please send your email first")
            return
        
        # Verify token
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE id = ? AND token = ?', (user_id, token))
        user = c.fetchone()
        conn.close()
        
        if not user:
            await update.message.reply_text("❌ Invalid token")
            return
        
        # Link telegram ID
        update_telegram_id(user_id, update.effective_user.id)
        
        expiry = datetime.fromisoformat(user['expires_at'])
        days_left = (expiry - datetime.now()).days
        
        await update.message.reply_text(
            f"✅ **Login Successful!**\n\n"
            f"Email: {user['email']}\n"
            f"Expires: {user['expires_at'][:10]} ({days_left} days)",
            parse_mode='Markdown'
        )
        
        await show_main_menu_message(update, context)
    
    else:
        await update.message.reply_text(
            "❌ Invalid format. Use:\n`email: your@email.com`\nor\n`token: YOUR-TOKEN`"
        )

async def show_main_menu(query, context):
    """Show main menu from callback"""
    keyboard = [
        [InlineKeyboardButton("📊 GET SIGNAL", callback_data='get_signal')],
        [InlineKeyboardButton("👤 Account", callback_data='account')],
        [InlineKeyboardButton("🚪 Logout", callback_data='logout')]
    ]
    await query.edit_message_text(
        "Main Menu:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_main_menu_message(update, context):
    """Show main menu from message"""
    keyboard = [
        [InlineKeyboardButton("📊 GET SIGNAL", callback_data='get_signal')],
        [InlineKeyboardButton("👤 Account", callback_data='account')],
        [InlineKeyboardButton("🚪 Logout", callback_data='logout')]
    ]
    await update.message.reply_text(
        "Main Menu:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_signal(query, context):
    """Send signal sticker"""
    if 'user_id' not in context.user_data:
        await query.edit_message_text("❌ Please login first")
        return
    
    try:
        response = requests.get(f"{API_URL}/api/signal", timeout=5)
        data = response.json()
        signal = data.get('signal', 'HOLD')
        
        sticker_id = STICKERS.get(signal, STICKERS['HOLD'])
        await query.message.reply_sticker(sticker_id)
        
        # Return to menu
        keyboard = [
            [InlineKeyboardButton("📊 GET SIGNAL", callback_data='get_signal')],
            [InlineKeyboardButton("👤 Account", callback_data='account')],
            [InlineKeyboardButton("🚪 Logout", callback_data='logout')]
        ]
        await query.message.reply_text(
            "Main Menu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        await query.message.reply_text(f"❌ Error")
        keyboard = [
            [InlineKeyboardButton("📊 GET SIGNAL", callback_data='get_signal')],
            [InlineKeyboardButton("👤 Account", callback_data='account')],
            [InlineKeyboardButton("🚪 Logout", callback_data='logout')]
        ]
        await query.message.reply_text(
            "Main Menu:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def show_account(query, context):
    """Show account info"""
    user_id = context.user_data.get('user_id')
    
    if not user_id:
        await query.edit_message_text("❌ Not logged in")
        return
    
    user = get_user_by_id(user_id)
    
    if not user:
        await query.edit_message_text("❌ User not found")
        return
    
    expiry = datetime.fromisoformat(user['expires_at'])
    days_left = (expiry - datetime.now()).days
    
    await query.edit_message_text(
        f"📧 **Email:** {user['email']}\n"
        f"📅 **Expires:** {user['expires_at'][:10]} ({days_left} days)\n"
        f"🔒 **Linked:** {'✅ Yes' if user['telegram_id'] else '❌ No'}",
        parse_mode='Markdown'
    )

# ============================
# MAIN
# ============================

def main():
    init_db()
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("\n" + "="*50)
    print("🤖 BRANVEE SIGNAL BOT")
    print("="*50)
    print("✅ Fixed imports")
    print("✅ Ready to run")
    print("="*50 + "\n")
    
    app.run_polling()

if __name__ == '__main__':
    main()
