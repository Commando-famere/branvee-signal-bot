"""
BRANVEE SIGNAL BOT - SIMPLE WORKING VERSION
"""

import logging
import sqlite3
import os
from datetime import datetime
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
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

# Conversation states
EMAIL, TOKEN = range(2)

# Database setup
os.makedirs('data', exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        token TEXT UNIQUE NOT NULL,
        telegram_id INTEGER,
        expires_at TIMESTAMP NOT NULL,
        is_suspended INTEGER DEFAULT 0
    )''')
    conn.commit()
    conn.close()
    print("✅ Database ready")

def get_user_by_email(email):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE LOWER(email) = LOWER(?)', (email,))
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

def link_telegram_id(user_id, telegram_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET telegram_id = ? WHERE id = ?', (telegram_id, user_id))
    conn.commit()
    conn.close()

# ============================
# HANDLERS
# ============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "📧 **BRANVEE GOLD SIGNAL**\n\nPlease enter your email:",
        parse_mode='Markdown'
    )
    return EMAIL

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    telegram_id = update.effective_user.id
    
    user = get_user_by_email(email)
    
    if not user:
        await update.message.reply_text("❌ Email not found")
        return EMAIL
    
    if user['is_suspended']:
        await update.message.reply_text("❌ Account suspended")
        return EMAIL
    
    now = datetime.now().isoformat()
    if user['expires_at'] < now:
        await update.message.reply_text("⚠️ Token expired")
        return EMAIL
    
    if user['telegram_id'] and user['telegram_id'] != telegram_id:
        await update.message.reply_text("❌ Already linked")
        return EMAIL
    
    context.user_data['user_id'] = user['id']
    context.user_data['email'] = user['email']
    context.user_data['expires_at'] = user['expires_at']
    context.user_data['auth_user'] = user
    
    await update.message.reply_text(
        f"✅ Email: {user['email']}\nNow enter token:"
    )
    return TOKEN

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip().upper()
    user = context.user_data.get('auth_user')
    telegram_id = update.effective_user.id
    
    if not user:
        await update.message.reply_text("❌ Session expired")
        return ConversationHandler.END
    
    if user['token'] != token:
        await update.message.reply_text("❌ Invalid token")
        return TOKEN
    
    if not user['telegram_id']:
        link_telegram_id(user['id'], telegram_id)
    
    expiry = datetime.fromisoformat(user['expires_at'])
    days_left = (expiry - datetime.now()).days
    
    await update.message.reply_text(
        f"✅ **Login Success!**\n\n"
        f"Email: {user['email']}\n"
        f"Expires: {user['expires_at'][:10]} ({days_left} days)",
        parse_mode='Markdown'
    )
    
    await show_menu(update, context)
    return ConversationHandler.END

async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 GET SIGNAL", callback_data='get_signal')],
        [InlineKeyboardButton("🔄 Strategy", callback_data='strategy_menu')]
    ]
    await update.message.reply_text(
        "Choose:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'get_signal':
        await send_signal(query, context)
    elif query.data == 'strategy_menu':
        await show_strategy_menu(query)
    elif query.data.startswith('strategy_'):
        strategy = query.data.replace('strategy_', '')
        context.user_data['strategy'] = strategy
        await query.edit_message_text(
            f"✅ Strategy: {strategy}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📊 GET SIGNAL", callback_data='get_signal')
            ]])
        )
    elif query.data == 'back':
        await show_menu_callback(query, context)

async def show_menu_callback(query, context):
    keyboard = [
        [InlineKeyboardButton("📊 GET SIGNAL", callback_data='get_signal')],
        [InlineKeyboardButton("🔄 Strategy", callback_data='strategy_menu')]
    ]
    await query.edit_message_text(
        "Choose:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_strategy_menu(query):
    keyboard = [
        [InlineKeyboardButton("Scalping", callback_data='strategy_SCALPING')],
        [InlineKeyboardButton("Trend", callback_data='strategy_TREND')],
        [InlineKeyboardButton("Pressure", callback_data='strategy_PRESSURE')],
        [InlineKeyboardButton("Fractals", callback_data='strategy_FRACTALS')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ]
    await query.edit_message_text(
        "Select Strategy:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_signal(query, context):
    try:
        response = requests.get(f"{API_URL}/api/signal", timeout=5)
        data = response.json()
        signal = data.get('signal', 'HOLD')
        
        sticker_id = STICKERS.get(signal, STICKERS['HOLD'])
        await query.message.reply_sticker(sticker_id)
        
        # Return to menu
        keyboard = [
            [InlineKeyboardButton("📊 GET SIGNAL", callback_data='get_signal')],
            [InlineKeyboardButton("🔄 Strategy", callback_data='strategy_menu')]
        ]
        await query.message.reply_text(
            "Choose:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        await query.message.reply_text("❌ Error")
        keyboard = [
            [InlineKeyboardButton("📊 GET SIGNAL", callback_data='get_signal')],
            [InlineKeyboardButton("🔄 Strategy", callback_data='strategy_menu')]
        ]
        await query.message.reply_text(
            "Choose:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled")
    return ConversationHandler.END

# ============================
# MAIN
# ============================

def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
            TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    app.add_handler(conv_handler)
    
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("\n" + "="*50)
    print("🤖 SIGNAL BOT READY")
    print("="*50)
    print("✅ Stickers loaded")
    print("✅ Ready to run")
    print("="*50 + "\n")
    
    app.run_polling()

if __name__ == '__main__':
    main()
