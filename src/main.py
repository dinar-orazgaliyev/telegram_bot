from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext, Updater
from typing import Final
import os, re, datetime
import spacy
from dateutil.parser import parse
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder 


load_dotenv()
nlp = spacy.load("en_core_web_sm")
TOKEN: Final = os.getenv('api_key')
BOT_USERNAME: Final = '@Jarvis_Reminder_Bot '


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Thanks for chatting with me I am Jarvis")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Please type smth so I can help")

async def city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    context.user_data['city_command_received'] = True
    
    await update.message.reply_text("Send me the city that you are currently in, so that the timezone is setup")
    

def extract_event_and_time(message):
    match = re.match(r"Remind me to (.+) (?:at|on)? (.+)", message, re.IGNORECASE) 
    if match:
        return match.group(1), match.group(2)
    return None, None

def process_time(time_str):
    doc = nlp(time_str)
    for ent in doc.ents:
        if ent.label_ == "TIME":
            return parse(ent.text)
    raise ValueError("Unsupported time format")

async def send_reminder(context: CallbackContext):
    job = context.job
    await context.bot.send_message(job.chat_id, text=f'Reminder of {job.data}')



def handle_city(city):
    
    g = Nominatim(user_agent="geoapiExercies")
    location = g.geocode(city)
    obj = TimezoneFinder()
    user_tz = obj.timezone_at(lng=location.longitude,lat=location.latitude)
    return user_tz


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_type: str = update.message.chat.type
    text: str = update.message.text
    processed: str = text.lower()
    print(f"User ({update.message.chat.id}) in {message_type}: '{text}'")
    if context.user_data['city_command_received']:
        user_tz = handle_city(text)
        context.user_data['city_command_received'] = False
    if "remind" in processed:
        event, date_time = extract_event_and_time(processed)

        if event and date_time:
            try:
                user_time = update.message.date
                user_time.replace(tzinfo=user_tz)
                reminder_time = process_time(date_time).replace(tzinfo=user_tz)


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
            await update.message.reply_text("Sorry, I couldn't understand your reminder message. Please provide the event and time together (e.g., 'Remind me to call my friend Tomorrow at 5pm').")
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
    #app.add_handler(MessageHandler(filters.TEXT, handle_city))
    

    # Errors
    app.add_error_handler(error)

    print("Polling...")
    app.run_polling(poll_interval=3)
