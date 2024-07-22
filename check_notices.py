import requests
import telegram
from datetime import datetime
import html
import os

# Placement Portal API details
NOTICES_API_URL = 'your_placement_portal_notices_api_url'
NOTICE_DETAILS_API_URL = 'your_placement_portal_notice_details_api_url'
COOKIE_NAME = '__Host-next-auth.csrf-token'
COOKIE_VALUE = os.environ.get('COOKIE_VALUE')

# Telegram Bot Token and Group Chat ID
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID')  # This will be a negative number

bot = telegram.Bot(token=TELEGRAM_TOKEN)

def fetch_data(url):
    cookies = {COOKIE_NAME: COOKIE_VALUE}
    headers = {'Content-Type': 'application/json'}
    
    response = requests.get(url, headers=headers, cookies=cookies)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching data: {response.status_code}")
        return None

def fetch_notice_details(notice_id):
    url = f"{NOTICE_DETAILS_API_URL}/{notice_id}"
    return fetch_data(url)

def is_new_notice(notice, last_check_time):
    notice_time = datetime.strptime(notice['updatedAt'], "%a %b %d %Y")
    return notice_time > last_check_time

def send_telegram_message(message):
    bot.send_message(chat_id=GROUP_CHAT_ID, text=message, parse_mode='HTML')

def check_notices():
    last_check_time = datetime.now()
    data = fetch_data(NOTICES_API_URL)
    
    if data and len(data) > 1:
        notices = data[1]['result']['data']['notices']
        
        for notice in notices:
            if is_new_notice(notice, last_check_time):
                details = fetch_notice_details(notice['id'])
                if details and len(details) > 0:
                    notice_data = details[0]['result']['data']
                    message = f"<b>New Notice:</b>\n"
                    message += f"<b>Title:</b> {notice_data['title']}\n"
                    message += f"<b>Posted by:</b> {notice['admin']}\n"
                    message += f"<b>Date:</b> {notice['updatedAt']}\n\n"
                    message += f"<b>Details:</b>\n{html.escape(notice_data['body'])}"
                    
                    if len(message) > 4096:
                        message = message[:4093] + "..."
                    
                    send_telegram_message(message)
    
    print("Notices checked successfully")

if __name__ == "__main__":
    check_notices()