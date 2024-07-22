import requests
import json
import os
import logging
from datetime import datetime
import asyncio
import aiohttp
from telegram import Bot

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Placement Portal API details
BASE_URL = 'https://www.aitplacements.in/api/trpc'
NOTICES_API_URL = f'{BASE_URL}/notice.publishedNoticeList,user.getUserProfileDetails?batch=1&input=%7B%220%22%3A%7B%22pageNos%22%3A1%7D%7D'
NOTICE_DETAILS_API_URL = f'{BASE_URL}/notice.noticeDetail'
COOKIE_VALUE = os.environ.get('COOKIE_VALUE')

# Telegram Bot Token and Group Chat ID
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')

bot = Bot(token=TELEGRAM_TOKEN)

# File to store the last processed notice ID
LAST_NOTICE_FILE = 'last_notice_id.txt'

async def fetch_data(url, params):
    cookies = {'__Secure-next-auth.csrf-token': COOKIE_VALUE}
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    logging.info(f"Fetching data from: {url}{params} \n {cookies}")
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, cookies=cookies, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                logging.error(f"Error fetching data: {response.status}")
                logging.error(f"Response content: {await response.text()}")
                return None

async def fetch_notices():
    data = await fetch_data(NOTICES_API_URL, {})
    print(data)
    if data and data[0]['result']['data']:
        notices = data[0]['result']['data']['notices']
        logging.info(f"Fetched {len(notices)} notices")
        return notices
    logging.warning("No notices found in the response")
    return []

async def fetch_notice_details(notice_id):
    params = {
    }
    data = await fetch_data("/notice.noticeDetail?batch=1&input=%7B%220%22%3A%7B%22id%22%3A%223d{notice_id}%22%7D%7D", params)
    if data and data[0]['result']['data']:
        logging.info(f"Fetched details for notice ID: {notice_id}")
        return data[0]['result']['data']
    logging.warning(f"No details found for notice ID: {notice_id}")
    return None

async def send_telegram_message(message):
    try:
        sent_message = await bot.send_message(chat_id=GROUP_CHAT_ID, text=message, parse_mode='HTML')
        logging.info(f"Message sent successfully. Message ID: {sent_message.message_id}")
    except Exception as e:
        logging.error(f"Error sending message: {str(e)}")
        logging.error(f"Error type: {type(e).__name__}")
        logging.error(f"Error args: {e.args}")

def get_last_processed_id():
    if os.path.exists(LAST_NOTICE_FILE):
        with open(LAST_NOTICE_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_last_processed_id(notice_id):
    with open(LAST_NOTICE_FILE, 'w') as f:
        f.write(notice_id)

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

async def test_telegram_connection():
    try:
        sent_message = await bot.send_message(chat_id=GROUP_CHAT_ID, text="Test message from placement bot")
        logging.info(f"Test message sent successfully. Message ID: {sent_message.message_id}")
    except Exception as e:
        logging.error(f"Error sending test message: {str(e)}")

async def check_telegram_api():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe') as response:
                logging.info(f"Telegram API response: {response.status}")
                logging.info(f"Response content: {await response.text()}")
    except Exception as e:
        logging.error(f"Error checking Telegram API: {str(e)}")

async def main():
    await check_telegram_api()
    await test_telegram_connection()
    await check_notices()

if __name__ == "__main__":
    asyncio.run(main())