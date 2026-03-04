"""
BRANVEE GOLD SIGNAL BOT - CORRECT FLOW
- GET SIGNAL button at bottom
- After signal, returns to same menu
- No extra messages
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

# ============================================
# CONFIGURATION
# ============================================

BOT_TOKEN = os.environ.get('SIGNAL_BOT_TOKEN', '8741454658:AAGlyxcVQMH7tKd13OmM2Y2VGa9ex9LbPfo')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 6980711942))
API_URL = os.environ.get('RAILWAY_API_URL', 'https://branvee-gold-system-production.up.railway.app')
DB_PATH = 'data/branvee.db'

os.makedirs('data', exist_ok=True)

# ============================================
# DATABASE
# ============================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        token TEXT UNIQUE NOT NULL,
        telegram_id INTEGER,
        expires_at TIMESTAMP NOT NULL,
        is_suspended BOOLEAN DEFAULT 0
    )''')
    conn.commit()
    conn.close()

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

# ============================================
# CONVERSATION STATES
# ============================================

EMAIL, TOKEN = range(2)

# ============================================
# AUTH HANDLERS
# ============================================

async function start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "📧 **BRANVEE GOLD SIGNAL** 📧\n\nPlease enter your registered email address:",
        parse_mode='Markdown'
    )
    return EMAIL

async function handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    email = update.message.text.strip()
    telegram_id = update.effective_user.id
    
    user = get_user_by_email(email)
    
    if not user:
        await update.message.reply_text("❌ Email not registered. Contact admin.")
        return EMAIL
    
    if user['is_suspended']:
        await update.message.reply_text("❌ Account suspended. Contact admin.")
        return EMAIL
    
    now = datetime.now().isoformat()
    if user['expires_at'] < now:
        await update.message.reply_text("⚠️ Token expired. Contact admin.")
        return EMAIL
    
    if user['telegram_id'] and user['telegram_id'] != telegram_id:
        await update.message.reply_text("❌ Account linked to another Telegram user.")
        return EMAIL
    
    context.user_data['auth_user'] = {
        'id': user['id'],
        'email': user['email'],
        'token': user['token'],
        'expires_at': user['expires_at'],
        'telegram_id': user['telegram_id']
    }
    context.user_data['telegram_id'] = telegram_id
    
    await update.message.reply_text(
        f"✅ Email found: {user['email']}\n\nNow enter your access token:"
    )
    return TOKEN

async function handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip().upper()
    user = context.user_data.get('auth_user')
    telegram_id = context.user_data.get('telegram_id')
    
    if not user:
        await update.message.reply_text("❌ Session expired. Please /start again.")
        return ConversationHandler.END
    
    if user['token'] != token:
        await update.message.reply_text("❌ Invalid token. Try again:")
        return TOKEN
    
    if not user['telegram_id']:
        link_telegram_id(user['id'], telegram_id)
    
    context.user_data['user_id'] = user['id']
    context.user_data['email'] = user['email']
    context.user_data['expires_at'] = user['expires_at']
    
    expiry = datetime.fromisoformat(user['expires_at'])
    days_left = (expiry - datetime.now()).days
    
    await update.message.reply_text(
        f"✅ **Login Successful!**\n\n"
        f"Email: {user['email']}\n"
        f"Expires: {user['expires_at'][:10]} ({days_left} days)\n"
        f"Account locked.",
        parse_mode='Markdown'
    )
    
    await show_main_menu(update, context)
    return ConversationHandler.END

async function show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show menu with GET SIGNAL at bottom"""
    
    message = "\n\n\n\n\n\n\n\n👑 **GET SIGNAL** 👑\n"
    
    keyboard = [
        [InlineKeyboardButton("👑 GET SIGNAL 👑", callback_data='get_signal')],
        [InlineKeyboardButton("Change Strategy", callback_data='menu_strategy')],
        [InlineKeyboardButton("Account Info", callback_data='menu_account')]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async function cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

# ============================================
# MENU HANDLERS
# ============================================

async function menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'get_signal':
        await handle_signal(query, context)
    elif data == 'menu_strategy':
        await show_strategy_menu(query)
    elif data == 'menu_account':
        await show_account_info(query, context)
    elif data == 'menu_main':
        await show_main_menu_callback(query, context)

async function show_main_menu_callback(query, context):
    """Show menu from callback"""
    message = "\n\n\n\n\n\n\n\n👑 **GET SIGNAL** 👑\n"
    
    keyboard = [
        [InlineKeyboardButton("👑 GET SIGNAL 👑", callback_data='get_signal')],
        [InlineKeyboardButton("Change Strategy", callback_data='menu_strategy')],
        [InlineKeyboardButton("Account Info", callback_data='menu_account')]
    ]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async function show_strategy_menu(query):
    keyboard = [
        [InlineKeyboardButton("📊 Scalping", callback_data='strategy_scalping')],
        [InlineKeyboardButton("📈 Trend", callback_data='strategy_trend')],
        [InlineKeyboardButton("📉 Pressure", callback_data='strategy_pressure')],
        [InlineKeyboardButton("📊 Fractals", callback_data='strategy_fractals')],
        [InlineKeyboardButton("🔙 Back", callback_data='menu_main')]
    ]
    
    await query.edit_message_text(
        "📊 **Select Strategy**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async function show_account_info(query, context):
    user_id = context.user_data.get('user_id')
    user = get_user_by_id(user_id)
    
    if not user:
        await query.edit_message_text("Error retrieving account.")
        return
    
    expiry = datetime.fromisoformat(user['expires_at'])
    days_left = (expiry - datetime.now()).days
    
    message = (
        f"📧 **Email:** {user['email']}\n"
        f"📅 **Expires:** {user['expires_at'][:10]} ({days_left} days)\n"
        f"🔒 **Linked:** {'Yes' if user['telegram_id'] else 'No'}"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data='menu_main')]]
    
    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async function strategy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    strategies = {
        'strategy_scalping': 'SCALPING',
        'strategy_trend': 'TREND',
        'strategy_pressure': 'PRESSURE',
        'strategy_fractals': 'FRACTALS'
    }
    
    if data in strategies:
        context.user_data['strategy'] = strategies[data]
        await query.edit_message_text(
            f"✅ Strategy: {strategies[data]}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("👑 GET SIGNAL 👑", callback_data='get_signal')
            ]]),
            parse_mode='Markdown'
        )

# ============================================
# SIGNAL HANDLER
# ============================================

async function handle_signal(query, context):
    """Handle GET SIGNAL - returns signal and returns to menu"""
    
    if 'user_id' not in context.user_data:
        await query.edit_message_text("Session expired. Please /start again.")
        return
    
    try:
        response = requests.get(f"{API_URL}/api/signal", timeout=5)
        data = response.json()
        signal = data.get('signal', 'HOLD')
        
        if signal == 'BUY':
            emoji = "🟢" * 16 + "\n" + "🟢" * 16 + "\n" + "🟢" * 16
        elif signal == 'SELL':
            emoji = "🔴" * 16 + "\n" + "🔴" * 16 + "\n" + "🔴" * 16
        else:
            emoji = "⚪" * 16 + "\n" + "⚪" * 16 + "\n" + "⚪" * 16
        
        # Send signal
        await query.message.reply_text(emoji)
        
        # Return to menu - EXACTLY as before
        message = "\n\n\n\n\n\n\n\n👑 **GET SIGNAL** 👑\n"
        
        keyboard = [
            [InlineKeyboardButton("👑 GET SIGNAL 👑", callback_data='get_signal')],
            [InlineKeyboardButton("Change Strategy", callback_data='menu_strategy')],
            [InlineKeyboardButton("Account Info", callback_data='menu_account')]
        ]
        
        await query.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        await query.message.reply_text("❌ Error")
        # Still return to menu
        await show_main_menu_callback(query, context)

# ============================================
# MAIN
# ============================================

def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Auth conversation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email)],
            TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
    app.add_handler(conv_handler)
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(menu_callback, pattern='^(get_signal|menu_)'))
    app.add_handler(CallbackQueryHandler(strategy_callback, pattern='^strategy_'))
    
    print("\n" + "="*60)
    print("🤖 BRANVEE SIGNAL BOT - CORRECT FLOW")
    print("="*60)
    print("✅ GET SIGNAL button at bottom")
    print("✅ Returns to same menu after signal")
    print("="*60 + "\n")
    
    app.run_polling()

if __name__ == '__main__':
    main()
