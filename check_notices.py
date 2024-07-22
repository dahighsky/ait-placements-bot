import requests
import telegram
import json
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Placement Portal API details
BASE_URL = 'https://www.aitplacements.in/api/trpc'
NOTICES_API_URL = f'{BASE_URL}/notice.publishedNoticeList'
NOTICE_DETAILS_API_URL = f'{BASE_URL}/notice.noticeDetail'
COOKIE_VALUE = os.environ.get('COOKIE_VALUE')

# Telegram Bot Token and Group Chat ID
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')

bot = telegram.Bot(token=TELEGRAM_TOKEN)

# File to store the last processed notice ID
LAST_NOTICE_FILE = 'last_notice_id.txt'

def fetch_data(url, params):
    cookies = {'__Host-next-auth.csrf-token': COOKIE_VALUE}
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    logging.info(f"Fetching data from: {url}")
    
    response = requests.get(url, headers=headers, cookies=cookies, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        logging.error(f"Error fetching data: {response.status_code}")
        logging.error(f"Response content: {response.text}")
        return None

def fetch_notices():
    params = {
        'batch': '1',
        'input': json.dumps({"0": {"pageNos": 1}})
    }
    data = fetch_data(NOTICES_API_URL, params)
    print(data)
    if data and data[1]['result']['data']:
        notices = data[1]['result']['data']['notices']
        logging.info(f"Fetched {len(notices)} notices")
        return notices
    logging.warning("No notices found in the response")
    return []

def fetch_notice_details(notice_id):
    params = {
        'batch': '1',
        'input': json.dumps({"0": {"id": notice_id}})
    }
    data = fetch_data(NOTICE_DETAILS_API_URL, params)
    if data and data[0]['result']['data']:
        logging.info(f"Fetched details for notice ID: {notice_id}")
        return data[0]['result']['data']
    logging.warning(f"No details found for notice ID: {notice_id}")
    return None

def send_telegram_message(message):
    try:
        bot.send_message(chat_id=GROUP_CHAT_ID, text=message, parse_mode='HTML')
        logging.info("Message sent successfully")
    except Exception as e:
        logging.error(f"Error sending message: {str(e)}")

def get_last_processed_id():
    if os.path.exists(LAST_NOTICE_FILE):
        with open(LAST_NOTICE_FILE, 'r') as f:
            return f.read().strip()
    return None

def save_last_processed_id(notice_id):
    with open(LAST_NOTICE_FILE, 'w') as f:
        f.write(notice_id)

def check_notices():
    last_processed_id = get_last_processed_id()
    logging.info(f"Last processed notice ID: {last_processed_id}")
    
    notices = fetch_notices()
    new_notices = []
    
    for notice in notices:
        if notice['id'] == last_processed_id:
            break
        new_notices.append(notice)
    
    new_notices.reverse()  # Process oldest to newest
    
    for notice in new_notices:
        details = fetch_notice_details(notice['id'])
        if details:
            message = f"<b>New Notice:</b>\n"
            message += f"<b>Title:</b> {details['title']}\n"
            message += f"<b>Posted by:</b> {details['admin']}\n"
            message += f"<b>Date:</b> {notice['updatedAt']}\n\n"
            message += f"<b>Details:</b>\n{details['body']}"
            
            if len(message) > 4096:
                message = message[:4093] + "..."
            
            send_telegram_message(message)
    
    if new_notices:
        save_last_processed_id(new_notices[-1]['id'])
        logging.info(f"Processed {len(new_notices)} new notices")
    else:
        logging.info("No new notices found")

if __name__ == "__main__":
    check_notices()