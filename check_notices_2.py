import requests
import os

url = "https://www.aitplacements.in/api/trpc/notice.publishedNoticeList,user.getUserProfileDetails?batch=1&input=%7B%220%22%3A%7B%22pageNos%22%3A1%7D%7D"

COOKIE_VALUE = os.environ.get('COOKIE_VALUE')
payload={}
headers = {'Cookie': COOKIE_VALUE}


response = requests.request("GET", url, headers=headers, data=payload)

print("################ IN CHECK NOTICES 2##################")
print(response.text)
