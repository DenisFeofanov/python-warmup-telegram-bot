from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import sqlite3
from datetime import datetime
import asyncio
import pytz
from dotenv import load_dotenv
import os

# Add at the beginning of your file
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Database initialization
def init_db():
    conn = sqlite3.connect('workout.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY,
            name TEXT,
            creator_id INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY,
            challenge_id INTEGER,
            name TEXT,
            target_reps INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS participants (
            challenge_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (challenge_id, user_id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS completions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            exercise_id INTEGER,
            reps_done INTEGER,
            date DATE
        )
    ''')
    conn.commit()
    conn.close()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Workout Challenge Bot!\n\n"
        "Commands:\n"
        "/new_challenge - Create a new challenge\n"
        "/my_challenges - View your challenges\n"
        "/complete - Log exercise completion\n"
        "/invite - Invite friends to challenge"
    )

async def new_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Let's create a new challenge! What's the name of your challenge?")
    context.user_data['creating_challenge'] = True

async def add_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'current_challenge' not in context.user_data:
        return
    
    challenge_id = context.user_data['current_challenge']
    text = update.message.text
    parts = text.split()
    
    if len(parts) >= 3:
        exercise_name = ' '.join(parts[:-1])
        target_reps = int(parts[-1])
        
        conn = sqlite3.connect('workout.db')
        c = conn.cursor()
        c.execute('INSERT INTO exercises (challenge_id, name, target_reps) VALUES (?, ?, ?)',
                 (challenge_id, exercise_name, target_reps))
        conn.commit()
        conn.close()

async def complete_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('workout.db')
    c = conn.cursor()
    
    # Get user's challenges and exercises
    c.execute('''
        SELECT e.id, e.name, e.target_reps, c.name
        FROM exercises e
        JOIN challenges c ON e.challenge_id = c.id
        JOIN participants p ON c.id = p.challenge_id
        WHERE p.user_id = ?
    ''', (user_id,))
    
    exercises = c.execute.fetchall()
    
    keyboard = []
    for exercise in exercises:
        keyboard.append([InlineKeyboardButton(
            f"{exercise[3]} - {exercise[1]} ({exercise[2]} reps)",
            callback_data=f"complete_{exercise[0]}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select exercise to complete:", reply_markup=reply_markup)

# Notification scheduler
async def check_incomplete_exercises():
    while True:
        now = datetime.now(pytz.UTC)
        if now.hour == 12 and now.minute == 0:
            conn = sqlite3.connect('workout.db')
            c = conn.cursor()
            # Check for incomplete exercises and send notifications
            # Implementation here
            conn.close()
        await asyncio.sleep(60)  # Check every minute

def main():
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new_challenge", new_challenge))
    app.add_handler(CommandHandler("complete", complete_exercise))
    
    # Start the bot
    app.run_polling()

if __name__ == '__main__':
    main() 