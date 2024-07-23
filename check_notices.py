import requests
import json
import os
import logging
from datetime import datetime
import asyncio
import aiohttp
from telegram import Bot
import re
from html import escape

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = 'https://www.aitplacements.in/api/trpc'
NOTICES_API_URL = 'https://www.aitplacements.in/api/trpc/notice.publishedNoticeList,user.getUserProfileDetails?batch=1&input=%7B%220%22%3A%7B%22pageNos%22%3A1%7D%7D'
NOTICE_DETAILS_API_URL = f'{BASE_URL}/notice.noticeDetail'
COOKIE_VALUE = os.environ.get('COOKIE_VALUE')

# Telegram Bot Token and Group Chat ID
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')

bot = Bot(token=TELEGRAM_TOKEN)

# File to store the last processed notice ID
LAST_NOTICE_FILE = 'last_notice_id.txt'

def fetch_data(url):
    headers = {
        'Cookie': COOKIE_VALUE,
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
        
    response = requests.request("GET", url, headers=headers)
    if response:
        return response.json()
    else:
        logging.error(f"Error fetching data: {response}")
        logging.error(f"Response content: {response}")
        return None

async def fetch_notices():
    data = fetch_data(NOTICES_API_URL)
    print(data)
    if data and data[0]['result']['data']:
        notices = data[0]['result']['data']['notices']
        logging.info(f"Fetched {len(notices)} notices")
        return notices
    logging.warning("No notices found in the response")
    return []

async def fetch_notice_details(notice_id):
    data = fetch_data(f"https://www.aitplacements.in/api/trpc/notice.noticeDetail?batch=1&input=%7B%220%22%3A%7B%22id%22%3A%22{notice_id}%22%7D%7D")
    if data and data[0]['result']['data']:
        logging.info(f"Fetched details for notice ID: {notice_id}")
        return data[0]['result']['data']
    logging.warning(f"No details found for notice ID: {notice_id}")
    return None

def format_message(message):
    # Replace &nbsp; with space
    message = message.replace('&nbsp;', ' ')
    
    # Remove any existing <b> tags to avoid duplication
    message = re.sub(r'</?b>', '', message)

    # Bold the main sections
    message = re.sub(r'(New Notice:)', r'<b>\1</b>', message)
    message = re.sub(r'(Title:)', r'<b>\1</b>', message)
    message = re.sub(r'(Date:)', r'<b>\1</b>', message)
    message = re.sub(r'(Details:)', r'<b>\1</b>', message)

    # Replace <p> tags with newlines
    message = re.sub(r'<p[^>]*>', '\n', message)
    message = re.sub(r'</p>', '\n', message)

    # Replace <br> tags with newlines
    message = re.sub(r'<br[^>]*>', '\n', message)

    # Replace multiple newlines with a single newline
    message = re.sub(r'\n+', '\n', message)

    # Replace <strong> tags with <b> tags
    message = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', message)

    # Handle links
    message = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'\2 (\1)', message)

    # Remove all other HTML tags
    message = re.sub(r'<[^>]+>', '', message)

    # Escape special characters for HTML
    message = escape(message)

    # Restore allowed HTML tags
    message = message.replace('&lt;b&gt;', '<b>')
    message = message.replace('&lt;/b&gt;', '</b>')

    return message.strip()

async def send_telegram_message(message):
    try:
        # Format the message
        formatted_message = format_message(message)

        # Split the message if it's too long
        max_length = 4096
        messages = [formatted_message[i:i+max_length] for i in range(0, len(formatted_message), max_length)]

        for msg in messages:
            sent_message = await bot.send_message(chat_id=GROUP_CHAT_ID, text=msg, parse_mode='HTML')
            logging.info(f"Message sent successfully. Message ID: {sent_message.message_id}")
    except Exception as e:
        logging.error(f"Error sending message: {str(e)}")
        logging.error(f"Error type: {type(e).__name__}")
        logging.error(f"Error args: {e.args}")
        logging.error(f"Formatted message: {formatted_message[:500]}...")  # Log the first 500 characters of the formatted message
        
        # Try sending without HTML parsing if there's an error
        try:
            sent_message = await bot.send_message(chat_id=GROUP_CHAT_ID, text=formatted_message[:4096])
            logging.info(f"Message sent without HTML parsing. Message ID: {sent_message.message_id}")
        except Exception as e2:
            logging.error(f"Error sending message without HTML parsing: {str(e2)}")
            
def get_last_processed_id():
    if os.path.exists(LAST_NOTICE_FILE):
        with open(LAST_NOTICE_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_last_processed_id(notice_id):
    try:
        with open(LAST_NOTICE_FILE, 'w') as f:
            f.write(notice_id)
        print(f"Successfully saved notice id: {notice_id}")
        print(f"File content after save: {open(LAST_NOTICE_FILE, 'r').read()}")
    except Exception as e:
        print(f"Error saving last processed id: {e}")
        
async def check_notices():
    last_processed_id = get_last_processed_id()
    logging.info(f"Last processed notice ID: {last_processed_id}")
    
    notices = await fetch_notices()
    new_notices = []
    
    for notice in notices:
        if notice['id'] == last_processed_id:
            break
        new_notices.append(notice)
    
    new_notices.reverse()  # Process oldest to newest
    
    for notice in new_notices:
        details = await fetch_notice_details(notice['id'])
        if details:
            message = f"<b>New Notice:</b>\n"
            message += f"<b>Title:</b> {details['title']}\n"
            message += f"<b>Date:</b> {notice['updatedAt']}\n\n"
            message += f"<b>Details:</b>\n{details['body']}"
            
            if len(message) > 4096:
                message = message[:4093] + "..."
            
            await send_telegram_message(message)
    
    if new_notices:
        save_last_processed_id(new_notices[-1]['id'])
        logging.info(f"Processed {len(new_notices)} new notices")
    else:
        logging.info("No new notices found")

async def main():
    await check_notices()

if __name__ == "__main__":
    asyncio.run(main())