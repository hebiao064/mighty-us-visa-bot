import requests
import configparser

from datetime import datetime


config = configparser.ConfigParser()
config.read('config.ini')


TELEGRAM_BOT_TOKEN = config['TELEGRAM']['TELEGRAM_BOT_TOKEN']
TELEGRAM_BOT_CHANNEL_DEBUG = config['TELEGRAM']['TELEGRAM_BOT_CHANNEL_DEBUG']
TELEGRAM_BOT_CHANNEL_PROD = config['TELEGRAM']['TELEGRAM_BOT_CHANNEL_PROD']

def MY_CONDITION(year, month, day): 
    return int(year) <= 2022 and (int(month) - int(datetime.now().month)) <= 3 

def send_notification(channel, msg):
    print(f"Sending msg: {msg}")

    if TELEGRAM_BOT_TOKEN and channel:
        print(f"Sending notification to telegram channel: {channel}")
        url = f"https://api.telegram.org/{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={channel}&parse_mode=MarkdownV2&text={msg}"
        
        try:
            result = requests.post(url)
            print(result.text)
        except Exception as e:
            print(e.message)


if __name__ == "__main__":
    # send_notification(TELEGRAM_BOT_CHANNEL_DEBUG, "Test Telegram API for debug channel")
    # send_notification(TELEGRAM_BOT_CHANNEL_PRDO, "Test Telegram API for prod channel")
    print(MY_CONDITION(2022, 12, 0))
    print(MY_CONDITION(2022, 11, 0))
    print(MY_CONDITION(2022, 10, 0))
    print(MY_CONDITION(2022, 9, 0))
    print(MY_CONDITION(2022, 8, 0))
    print(MY_CONDITION(2022, 7, 0))
    print(MY_CONDITION(2023, 1, 0))

    send_notification(TELEGRAM_BOT_CHANNEL_PROD, "Crashed\! Need HELP\!")