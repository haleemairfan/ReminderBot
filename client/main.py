from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
from threading import Thread
from typing import Final

from dotenv import load_dotenv  
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton  
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler




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


async def viewCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    current_date = datetime.now().date()
    days_until_end_of_week = 6 - current_date.weekday()


    buttons = []

    for i in range(days_until_end_of_week + 1):
        day = current_date + timedelta(days=i)
        day_str = day.strftime('%A, %d %B')
        buttons.append([InlineKeyboardButton(day_str, callback_data=f'view_reminder_{day}')])
    
    buttons.append([InlineKeyboardButton("Exit", callback_data='exit')])

    response = InlineKeyboardMarkup(buttons)
    await update.message.reply_text(
        "Let’s view your reminders", reply_markup=response
    )

async def setCommand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Create my reminders!", callback_data='create_reminders')]
    ]
    response = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Let's set some reminders!", reply_markup=response
    )


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
        await setReminder(update, context, selected_date)
    elif query.data  == 'store_reminder':
        context.user_data['awaiting_reminder'] = True
        await query.message.reply_text('Please enter your reminder')
    elif query.data == 'exit':
        await exit(update, context)
    elif query.data.startswith('view_reminder_'):
        selected_date_str = query.data.replace('view_reminder_', '')
        selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
        await viewReminder(update, context, selected_date)
            

async def setReminder(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: datetime.date):
    formatted_date = selected_date.strftime("%A, %d %B %Y")
    keyboard = [
        [InlineKeyboardButton("Enter your reminder!", callback_data='store_reminder')],
        [InlineKeyboardButton("I have no more reminders!", callback_data='create_reminders')]
    ]

    response = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.reply_text(
            f'Please enter your reminders for {formatted_date}:', reply_markup=response
        )
    else:
        await update.message.reply_text(
            f'Please enter your reminders for {formatted_date}:', reply_markup=response
        )

async def storeReminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_reminder'):
        text = update.message.text
        context.user_data['content'] = text
        context.user_data['awaiting_reminder'] = False
        context.user_data['awaiting_time'] = True
        await update.message.reply_text('Please enter the time for your reminder (HH:MM)')
    
async def storeTime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if context.user_data.get('awaiting_time'):
            text = update.message.text
            selected_time = datetime.strptime(text, "%H:%M").time()
            context.user_data['awaiting_time'] = False
            selected_date = context.user_data.get('selected_date')

            reminder_data = {
                "user_id": update.message.from_user.id,
                "content": context.user_data.get('content'),
                "date": selected_date.strftime("%Y-%m-%d"),
                "time": selected_time.strftime("%H:%M")
            }
            response = requests.post("https://reminder-bot-api.onrender.com/storeReminders",
                          json=reminder_data)
            if response.status_code == 201:
                await update.message.reply_text(f"Reminder saved: {reminder_data['content']} on {reminder_data['date']} at {reminder_data['time']}")
            else:
                await update.message.reply_text(f"Failed to save reminder: {response.status_code}")

            # Clear the state
            context.user_data.pop('content', None)
            context.user_data.pop('awaiting_time', None)
            context.user_data.pop('awaiting_reminder', None)

            await setReminder(update, context, selected_date)
    except ValueError:
        await update.message.reply_text("Invalid time format. Please enter the time in HH:MM format.")

async def viewReminder(update: Update, context: ContextTypes.DEFAULT_TYPE, selected_date: datetime):
    try:
        user_id = update.callback_query.from_user.id  # Get the user ID
        response = requests.get(
            f"https://reminder-bot-api.onrender.com/viewReminders?date={selected_date.strftime('%Y-%m-%d')}&user_id={user_id}"
        )

        if response.status_code == 200:
            # Parse the response data
            data = response.json()
            reminders = data.get("data", [])
            
            reminder_string = [f"- {reminder['time']}: {reminder['content']}" for reminder in reminders]
            message = f"Reminders for {selected_date.strftime('%A, %d %B %Y')}:\n" + "\n".join(reminder_string)
            
            await update.callback_query.message.reply_text(message)
        else:
            await update.callback_query.message.reply_text(
                f"Failed to retrieve reminders. Status code: {response.status_code}. Response: {response.text}"
            )
    except Exception as e:
        await update.callback_query.message.reply_text(f"An error occurred: {str(e)}")


async def exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("Okay! See ya next time!")
    

# Responses
async def handleResponse(text: str) -> str:
    return 'Please refer to /help if you require any help using this bot'

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
        await storeReminder(update, context)
    elif context.user_data.get('awaiting_time'):
        await storeTime(update, context)
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

    buttons.append([InlineKeyboardButton("Exit", callback_data='exit')])
    
    response = InlineKeyboardMarkup(buttons)
    await update.callback_query.message.reply_text(
        "Let’s create your reminders", reply_markup=response
    )

    

# Logging errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')



class simpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running.")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()


def run_dummy_server():
    port = int(os.environ.get("PORT", 5001))
    server = HTTPServer(("0.0.0.0", port), simpleHTTPRequestHandler)
    server.serve_forever()


# String all the functions together
if __name__ == '__main__':
    print('starting bot')
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler('start', startCommand))
    app.add_handler(CommandHandler('set', setCommand))
    app.add_handler(CommandHandler('view', viewCommand))
    app.add_handler(CommandHandler('help', helpCommand))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handleMessage))

    # CallbackQuery handler for buttons
    app.add_handler(CallbackQueryHandler(button))

    # Errors
    app.add_error_handler(error)


    Thread(target=run_dummy_server).start()

    print('polling')
    app.run_polling(poll_interval=3)