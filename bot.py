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
    
    # Challenges table
    c.execute('''
        CREATE TABLE IF NOT EXISTS challenges
        (id TEXT PRIMARY KEY,
         name TEXT NOT NULL,
         creator_id INTEGER NOT NULL,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    ''')
    
    # Challenge members table
    c.execute('''
        CREATE TABLE IF NOT EXISTS challenge_members
        (challenge_id TEXT,
         user_id INTEGER,
         joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         PRIMARY KEY (challenge_id, user_id),
         FOREIGN KEY (challenge_id) REFERENCES challenges(id))
    ''')
    
    # Challenge completions table - modified to store completion_date separately
    c.execute('''
        CREATE TABLE IF NOT EXISTS challenge_completions
        (challenge_id TEXT,
         user_id INTEGER,
         completion_date DATE,
         completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
         PRIMARY KEY (challenge_id, user_id, completion_date),
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
        "/join <id> - Join an existing challenge\n"
        "/leave <id> - Leave a challenge\n"
        "/status - View your challenges\n"
        "/complete <id> - Complete a challenge\n"
        "/help - Show this help message"
    )

async def new_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a challenge name: /new <name>")
        return

    name = ' '.join(context.args)
    challenge_id = f"ch_{int(datetime.now().timestamp())}"[-6:]
    user_id = update.effective_user.id

    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    
    # Create challenge
    c.execute('INSERT INTO challenges (id, name, creator_id) VALUES (?, ?, ?)', 
             (challenge_id, name, user_id))
    
    # Add creator as first member
    c.execute('INSERT INTO challenge_members (challenge_id, user_id) VALUES (?, ?)',
             (challenge_id, user_id))
    
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"Challenge created!\n"
        f"ID: {challenge_id}\n"
        f"Name: {name}\n\n"
        f"Share this ID with others so they can join using /join {challenge_id}"
    )

async def join_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a challenge ID: /join <id>")
        return

    challenge_id = context.args[0]
    user_id = update.effective_user.id

    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()

    # Check if challenge exists
    c.execute('SELECT name FROM challenges WHERE id = ?', (challenge_id,))
    challenge = c.fetchone()
    
    if not challenge:
        await update.message.reply_text("Challenge not found!")
        conn.close()
        return

    # Check if already a member
    c.execute('''
        SELECT 1 FROM challenge_members 
        WHERE challenge_id = ? AND user_id = ?
    ''', (challenge_id, user_id))
    
    if c.fetchone():
        await update.message.reply_text("You're already a member of this challenge!")
    else:
        c.execute('INSERT INTO challenge_members (challenge_id, user_id) VALUES (?, ?)',
                 (challenge_id, user_id))
        conn.commit()
        await update.message.reply_text(f"You've joined the challenge: {challenge[0]} 🎯")
    
    conn.close()

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = datetime.now().date().isoformat()
    
    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    
    c.execute('''
        SELECT 
            c.id,
            c.name,
            CASE WHEN cc.user_id IS NOT NULL THEN 1 ELSE 0 END as completed,
            (SELECT COUNT(*) FROM challenge_members cm2 WHERE cm2.challenge_id = c.id) as member_count
        FROM challenges c
        JOIN challenge_members cm ON c.id = cm.challenge_id
        LEFT JOIN challenge_completions cc 
            ON c.id = cc.challenge_id 
            AND cc.user_id = ?
            AND cc.completion_date = ?
        WHERE cm.user_id = ?
        ORDER BY c.created_at DESC
    ''', (user_id, today, user_id))
    
    challenges = c.fetchall()
    conn.close()

    if not challenges:
        await update.message.reply_text(
            "You haven't joined any challenges yet.\n"
            "Create one with /new <name> or join existing with /join <id>"
        )
        return

    status_text = "Your Challenges:\n\n"
    for ch_id, name, completed, member_count in challenges:
        status = "✅" if completed else "❌"
        status_text += f"{ch_id}: {name} {status} (Members: {member_count})\n"

    await update.message.reply_text(status_text)

async def leave_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a challenge ID: /leave <id>")
        return

    challenge_id = context.args[0]
    user_id = update.effective_user.id

    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    
    c.execute('DELETE FROM challenge_members WHERE challenge_id = ? AND user_id = ?',
             (challenge_id, user_id))
    
    if c.rowcount > 0:
        conn.commit()
        await update.message.reply_text("You've left the challenge!")
    else:
        await update.message.reply_text("You're not a member of this challenge!")
    
    conn.close()

async def complete_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please provide a challenge ID: /complete <id>")
        return

    challenge_id = context.args[0]
    user_id = update.effective_user.id
    today = datetime.now().date().isoformat()  # Get today's date in YYYY-MM-DD format
    
    conn = sqlite3.connect('warmup_challenges.db')
    c = conn.cursor()
    
    # Check if challenge exists and user is a member
    c.execute('''
        SELECT 1 FROM challenges c
        JOIN challenge_members cm ON c.id = cm.challenge_id
        WHERE c.id = ? AND cm.user_id = ?
    ''', (challenge_id, user_id))
    
    if not c.fetchone():
        await update.message.reply_text("Challenge not found or you're not a member!")
        conn.close()
        return

    # Check if already completed today
    c.execute('''
        SELECT 1 FROM challenge_completions 
        WHERE challenge_id = ? AND user_id = ? AND completion_date = ?
    ''', (challenge_id, user_id, today))
    
    if c.fetchone():
        await update.message.reply_text("You've already completed this challenge today! 🎯")
    else:
        # Add completion record
        c.execute('''
            INSERT INTO challenge_completions (challenge_id, user_id, completion_date)
            VALUES (?, ?, ?)
        ''', (challenge_id, user_id, today))
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
    application.add_handler(CommandHandler("join", join_challenge))
    application.add_handler(CommandHandler("leave", leave_challenge))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("complete", complete_challenge))

    application.run_polling()

if __name__ == '__main__':
    main()