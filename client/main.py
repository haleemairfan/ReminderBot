import requests
from typing import Final
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os



load_dotenv()

TOKEN: Final = os.getenv("BOT_TOKEN")
BOT_USERNAME: Final = '@remindersUsingABot'




# Commands
async def startCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Creating buttons
    keyboard = [
        [InlineKeyboardButton("Create my reminders!", callback_data='create_reminders')]
    ]

    response = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Hello! Let's get you started!", reply_markup=response
    )


async def helpCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Type your tasks into this bot')


async def customCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('This is a custom command')


# Callback query handler for button clicks
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'create_reminders':
        await handleReminderCreation(update, context)
    elif query.data.startswith('set_reminder_'):
        selected_date_str = query.data.replace('set_reminder_', '')
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        context.user_data['selected_date'] = selected_date
        await set_reminder(update, context, selected_date)
    elif query.data  == 'store_reminder':
        context.user_data['awaiting_reminder'] = True
        await query.message.reply_text('Please enter your reminder')

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: datetime.date):
    formatted_date = selected_date.strftime("%A, %d %B %Y")
    keyboard = [
        [InlineKeyboardButton("Enter your reminder!", callback_data='store_reminder')],
        [InlineKeyboardButton("I have no more reminders!", callback_data='select_day')]
    ]

    response = InlineKeyboardMarkup(keyboard)
    await update.callback_query.message.reply_text(
        f'Please enter your reminders for {formatted_date}:', reply_markup=response
    )

async def store_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_reminder'):
        text = update.message.text
        context.user_data['content'] = text
        context.user_data['awaiting_reminder'] = False
        context.user_data['awaiting_time'] = True
        await update.message.reply_text('Please enter the time for your reminder (HH:MM)')
    
async def store_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.user_data.get('awaiting_time'):
            text = update.message.text
            selected_time = datetime.strptime(text, "%H:%M").time()
            context.user_data['awaiting time'] = False
            selected_date = context.user_data.get('selected_date')

            reminder_data = {
                "content": context.user_data.get('content'),
                "date": selected_date.strftime("%Y-%m-%d"),
                "time": selected_time.strftime("%H:%M")
            }

            print(f"Reminder stored: {reminder_data}")
            await update.message.reply_text(f"Reminder saved: {reminder_data['content']} on {reminder_data['date']} at {reminder_data['time']}")

            # Clear the state
            context.user_data.clear()



    except ValueError:
        await update.message.reply_text("Invalid time format. Please enter the time in HH:MM format.")


        

# Responses
async def handleResponse(text: str) -> str:
    processed: str = text.lower()

    if 'hello' in processed:
        return 'i fucked ur mom'
    if 'how are you' in processed:
        return 'ur mother'
    if 'ur mother' in processed:
        return 'ur auntie'
    return 'GAY RIGHTS!'


async def handleMessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Group chat or private chat
    messageType: str = update.message.chat.type

    # Incoming message
    text: str = update.message.text

    # UserID for debugging
    print(f'User ({update.message.chat.id}) in {messageType}: "{text}"')

    if messageType == "group":
        if BOT_USERNAME in text:
            newText: str = text.replace(BOT_USERNAME, '')
            response: str = await handleResponse(newText)
        else:
            return
    elif context.user_data.get('awaiting_reminder'):
        await store_reminder(update, context)
    elif context.user_data.get('awaiting_time'):
        await store_time(update, context)
    else:
        response: str = await handleResponse(text)

    print('Bot: ', response)

    await update.message.reply_text(response)


# Reminder creation for a week
async def handleReminderCreation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_date = datetime.now().date()
    days_until_end_of_week = 6 - current_date.weekday()


    buttons = []

    for i in range(days_until_end_of_week + 1):
        day = current_date + timedelta(days=i)
        day_str = day.strftime('%A, %d %B')
        buttons.append([InlineKeyboardButton(day_str, callback_data=f'set_reminder_{day}')])
    
    response = InlineKeyboardMarkup(buttons)
    await update.callback_query.message.reply_text(
        "Let’s create your reminders", reply_markup=response
    )

    

# Logging errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')


# String all the functions together
if __name__ == '__main__':
    print('starting bot')
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', startCommand))
    app.add_handler(CommandHandler('help', helpCommand))
    app.add_handler(CommandHandler('custom', customCommand))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handleMessage))

    # CallbackQuery handler for buttons
    app.add_handler(CallbackQueryHandler(button))

    # Errors
    app.add_error_handler(error)

    print('polling')
    app.run_polling(poll_interval=3)