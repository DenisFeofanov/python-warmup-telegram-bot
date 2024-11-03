import os
import logging
from datetime import datetime, time
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Database setup
def setup_database():
    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    # Challenges table - stores challenge definitions
    c.execute('''
        CREATE TABLE IF NOT EXISTS challenges
        (id TEXT PRIMARY KEY,
         name TEXT NOT NULL,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    ''')
    # Challenge completions table - stores user-specific completions
    c.execute('''
        CREATE TABLE IF NOT EXISTS challenge_completions
        (challenge_id TEXT,
         user_id INTEGER,
         completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         PRIMARY KEY (challenge_id, user_id),
         FOREIGN KEY (challenge_id) REFERENCES challenges(id))
    ''')
    conn.commit()
    conn.close()

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Daily Warmup Tracker!\n\n"
        "Commands:\n"
        "/new <name> - Create a new challenge\n"
        "/status - View all challenges\n"
        "/complete <id> - Complete a challenge\n"
        "/help - Show this help message"
    )

async def new_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a challenge name: /new <name>")
        return

    name = ' '.join(context.args)
    challenge_id = f"ch_{int(datetime.now().timestamp())}"[-6:]  # Generate short ID

    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    c.execute('INSERT INTO challenges (id, name) VALUES (?, ?)', (challenge_id, name))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"Challenge created!\nID: {challenge_id}\nName: {name}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    # Modified query to check user-specific completions
    c.execute('''
        SELECT c.id, c.name, CASE WHEN cc.user_id IS NOT NULL THEN 1 ELSE 0 END as completed
        FROM challenges c
        LEFT JOIN challenge_completions cc 
            ON c.id = cc.challenge_id 
            AND cc.user_id = ?
            AND date(cc.completed_at) = date('now')
    ''', (user_id,))
    challenges = c.fetchall()
    conn.close()

    if not challenges:
        await update.message.reply_text("No challenges found. Create one with /new <name>")
        return

    status_text = "Current Challenges:\n\n"
    for ch_id, name, completed in challenges:
        status = "✅" if completed else "❌"
        status_text += f"{ch_id}: {name} {status}\n"

    await update.message.reply_text(status_text)

async def complete_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a challenge ID: /complete <id>")
        return

    challenge_id = context.args[0]
    user_id = update.effective_user.id
    
    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    
    # Check if challenge exists
    c.execute('SELECT id FROM challenges WHERE id = ?', (challenge_id,))
    if not c.fetchone():
        await update.message.reply_text("Challenge not found!")
        conn.close()
        return

    # Check if already completed today
    c.execute('''
        SELECT 1 FROM challenge_completions 
        WHERE challenge_id = ? AND user_id = ? 
        AND date(completed_at) = date('now')
    ''', (challenge_id, user_id))
    
    if c.fetchone():
        await update.message.reply_text("You've already completed this challenge today! 🎯")
    else:
        # Add completion record
        c.execute('''
            INSERT INTO challenge_completions (challenge_id, user_id)
            VALUES (?, ?)
        ''', (challenge_id, user_id))
        conn.commit()
        await update.message.reply_text(f"Challenge {challenge_id} completed! 🎉")
    
    conn.close()

def main():
    setup_database()
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("new", new_challenge))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("complete", complete_challenge))

    # Remove the job queue setup since we don't need daily reset anymore
    application.run_polling()

if __name__ == '__main__':
    main()