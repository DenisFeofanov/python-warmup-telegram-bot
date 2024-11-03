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
    c.execute('''
        CREATE TABLE IF NOT EXISTS challenges
        (id TEXT PRIMARY KEY,
         name TEXT NOT NULL,
         completed BOOLEAN DEFAULT FALSE,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
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
    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    c.execute('SELECT id, name, completed FROM challenges')
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
    
    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    c.execute('UPDATE challenges SET completed = TRUE WHERE id = ?', (challenge_id,))
    if c.rowcount == 0:
        await update.message.reply_text("Challenge not found!")
    else:
        conn.commit()
        await update.message.reply_text(f"Challenge {challenge_id} completed! 🎉")
    conn.close()

async def reset_daily(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    c.execute('UPDATE challenges SET completed = FALSE')
    conn.commit()
    conn.close()
    logging.info("Daily challenges reset")

def main():
    # Set up database
    setup_database()

    # Initialize bot
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("new", new_challenge))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("complete", complete_challenge))

    # Schedule daily reset at midnight
    job_queue = application.job_queue
    job_queue.run_daily(reset_daily, time(hour=0, minute=0))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()