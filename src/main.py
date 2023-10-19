from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext, Updater
from typing import Final
import os, re
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder 
import pytz

load_dotenv()
TOKEN: Final = os.getenv('api_key')
BOT_USERNAME: Final = '@Jarvis_Reminder_Bot '


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command. Respond with a welcome message.
    """
    await update.message.reply_text("Hello! Thanks for chatting with me I am Jarvis")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /help command. Provide instructions to the user.
    """
    await update.message.reply_text("Hello! Please type smth so I can help")

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /city command. Prompt the user to send their current city for timezone setup.
    """
    context.user_data['city_command_received'] = True
    
    await update.message.reply_text("Send me the city that you are currently in, so that the timezone is setup")
    

def extract_event_and_time(message):
    """
    Extract the event and datetime from a user message.
    Args:
        message (str): The user's message.
    Returns:
        event (str): The event extracted from the message.
        datetime_str (str): The datetime extracted from the message.
    """
    match = re.search(r"Remind me to (.+?) (?:on|at)? (\d{2}\.\d{2}\.\d{4} at \d{2}:\d{2})", message, re.IGNORECASE)
    if match:
        event = match.group(1)
        datetime_str = match.group(2)
        return event, datetime_str
    return None, None

async def send_reminder(context: CallbackContext):
    """
    Send a reminder message to the user.
    Args:
        context (CallbackContext): The callback context.
    """
    job = context.job
    await context.bot.send_message(job.chat_id, text=f'Reminder of {job.data}')



def handle_city(city):
    """
    Get the user's timezone based on their current city.
    Args:
        city (str): The user's current city.
    Returns:
        user_tz (str): The user's timezone.
    """
    g = Nominatim(user_agent="geoapiExercies")
    location = g.geocode(city)
    obj = TimezoneFinder()
    user_tz = obj.timezone_at(lng=location.longitude,lat=location.latitude)

    return user_tz


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle user messages, process reminders, and set up timezones.
    Args:
        update (Update): The Telegram update object.
        context (ContextTypes.DEFAULT_TYPE): The context for the handler.
    """
    message_type: str = update.message.chat.type
    text: str = update.message.text
    processed: str = text.lower()
    
    if context.user_data['city_command_received']:
        user_tz = handle_city(text)
        context.user_data['city_command_received'] = False
        context.user_data['user_tz'] = user_tz
        
        await update.message.reply_text("Ok great, your timezone is figured out")
    if "remind" in processed:
        event, date_time = extract_event_and_time(processed)
        
        if event and date_time:
            try:
                user_time = update.message.date
                
                user_tz = context.user_data['user_tz']
                user_tz = pytz.timezone(user_tz)
                user_time = user_time.astimezone(user_tz)
                reminder_time = parse(date_time)#.astimezone(user_tz)
                reminder_time = user_tz.localize(reminder_time)
                
                if reminder_time > user_time:
                    
                    chat_id = update.message.chat_id
                    
                    rem_sec = (reminder_time - user_time).total_seconds()
                    
                    context.job_queue.run_once(callback=send_reminder, when=rem_sec,data=event,name=str(chat_id), chat_id=chat_id)
                    await update.message.reply_text(f"Great! I'll remind you of '{event}' at {reminder_time}.")
                else:
                    await update.message.reply_text("The time you specified is in the past, please write future time")
            except ValueError:
                await update.message.reply_text("I could not understand the time format")
        else:
            await update.message.reply_text("Sorry, I couldn't understand your reminder message. Please provide the event and time together with exact date and time. Eg: (Remind me to call a friend on 21.11.23 at 19:00)")
    else:
        return
    
    

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    print("Starting the bot...")
    app = Application.builder().token(TOKEN).build()

    
    # Commands
    app.add_handler(CommandHandler('start',start_command))
    app.add_handler(CommandHandler('help',help_command))
    app.add_handler(CommandHandler('city', city))

    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))

    

    # Errors
    app.add_error_handler(error)

    print("Polling...")
    app.run_polling(poll_interval=3)
