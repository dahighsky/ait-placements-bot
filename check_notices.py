import requests
import telegram
from datetime import datetime
import html
import os
import json

# Placement Portal API details
BASE_URL = 'https://www.aitplacements.in/api/trpc'
NOTICES_API_URL = f'{BASE_URL}/notice.publishedNoticeList'
NOTICE_DETAILS_API_URL = f'{BASE_URL}/notice.noticeDetail'
COOKIE_VALUE = os.environ.get('COOKIE_VALUE')

# Telegram Bot Token and Group Chat ID
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def fetch_data(url, params):
    cookies = {'__Host-next-auth.csrf-token': COOKIE_VALUE}
    headers = {
        'Content-Type': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, cookies=cookies, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

def fetch_notices():
    params = {
        'batch': '1',
        'input': json.dumps({"0": {"pageNos": 1}})
    }
    data = fetch_data(NOTICES_API_URL, params)
    if data and data[0]['result']['data']:
        return data[0]['result']['data']['notices']
    return []

def fetch_notice_details(notice_id):
    params = {
        'batch': '1',
        'input': json.dumps({"0": {"id": notice_id}})
    }
    data = fetch_data(NOTICE_DETAILS_API_URL, params)
    if data and data[0]['result']['data']:
        return data[0]['result']['data']
    return None

def is_new_notice(notice, last_check_time):
    notice_time = datetime.strptime(notice['updatedAt'], "%a %b %d %Y")
    return notice_time > last_check_time

def send_telegram_message(message):
    bot.send_message(chat_id=GROUP_CHAT_ID, text=message, parse_mode='HTML')

def check_notices():
    last_check_time = datetime.now()
    notices = fetch_notices()
    
    for notice in notices:
        if is_new_notice(notice, last_check_time):
            details = fetch_notice_details(notice['id'])
            if details:
                message = f"<b>New Notice:</b>\n"
                message += f"<b>Title:</b> {details['title']}\n"
                message += f"<b>Posted by:</b> {details['admin']}\n"
                message += f"<b>Date:</b> {notice['updatedAt']}\n\n"
                message += f"<b>Details:</b>\n{html.escape(details['body'])}"
                
                if len(message) > 4096:
                    message = message[:4093] + "..."
                
                send_telegram_message(message)
    
    print("Notices checked successfully")

if __name__ == "__main__":
    check_notices()