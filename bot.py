import os
from datetime import datetime, time
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
from database import Database

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# States for conversation handler
EXERCISE, REPS = range(2)

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Morning Workout Bot! 💪\n\n"
        "Commands:\n"
        "/set_challenge - Set a new exercise challenge\n"
        "/my_challenges - View your current challenges\n"
        "/complete - Mark an exercise as complete"
    )

async def set_challenge_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("What exercise would you like to add? (e.g., pushups, squats)")
    return EXERCISE

async def set_challenge_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['exercise'] = update.message.text.lower()
    await update.message.reply_text("How many repetitions per day?")
    return REPS

async def set_challenge_reps(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        reps = int(update.message.text)
        exercise = context.user_data['exercise']
        user_id = update.effective_user.id
        
        db.set_challenge(user_id, exercise, reps)
        await update.message.reply_text(f"Challenge set: {reps} {exercise} per day!")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return REPS

async def my_challenges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    challenges = db.get_challenges(user_id)
    
    if not challenges:
        await update.message.reply_text("You haven't set any challenges yet. Use /set_challenge to add one!")
        return

    message = "Your daily challenges:\n\n"
    for exercise, reps in challenges:
        message += f"• {reps} {exercise}\n"
    
    await update.message.reply_text(message)

async def complete_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    challenges = db.get_challenges(user_id)
    
    if not challenges:
        await update.message.reply_text("You haven't set any challenges yet!")
        return

    keyboard = []
    for exercise, reps in challenges:
        keyboard.append([InlineKeyboardButton(f"{exercise} ({reps} reps)", callback_data=f"complete_{exercise}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Which exercise did you complete?", reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    exercise = query.data.replace("complete_", "")
    user_id = query.from_user.id
    
    # Get target reps for this exercise
    challenges = dict(db.get_challenges(user_id))
    target_reps = challenges.get(exercise)
    
    db.mark_exercise_complete(user_id, exercise, target_reps)
    await query.edit_message_text(f"Marked {target_reps} {exercise} as complete! 💪")

async def check_incomplete_exercises(context: ContextTypes.DEFAULT_TYPE):
    # Get all users with incomplete exercises
    job = context.job
    user_id = job.data  # Assuming job.data contains user_id
    
    incomplete = db.get_incomplete_exercises(user_id)
    if incomplete:
        message = "You still haven't completed these exercises today:\n\n"
        for exercise, reps in incomplete:
            message += f"• {reps} {exercise}\n"
        
        await context.bot.send_message(chat_id=user_id, text=message)

def main():
    app = Application.builder().token(os.getenv('BOT_TOKEN')).build()

    # Add conversation handler for setting challenges
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('set_challenge', set_challenge_start)],
        states={
            EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_challenge_exercise)],
            REPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_challenge_reps)]
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("my_challenges", my_challenges))
    app.add_handler(CommandHandler("complete", complete_exercise))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Schedule daily reminder at 12:00
    job_queue = app.job_queue
    reminder_time = time(12, 0)  # 12:00
    job_queue.run_daily(check_incomplete_exercises, reminder_time)

    app.run_polling()

if __name__ == '__main__':
    main()
