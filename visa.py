# -*- coding: utf8 -*-

from logging import exception
import time
import json
import random
import platform
import configparser
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


config = configparser.ConfigParser()
config.read('config.ini')

USERNAME = config['USVISA']['USERNAME']
PASSWORD = config['USVISA']['PASSWORD']
SCHEDULE_ID = config['USVISA']['SCHEDULE_ID']
MY_SCHEDULE_DATE = config['USVISA']['MY_SCHEDULE_DATE']

TELEGRAM_BOT_TOKEN = config['TELEGRAM']['TELEGRAM_BOT_TOKEN']
TELEGRAM_BOT_CHANNEL_DEBUG = config['TELEGRAM']['TELEGRAM_BOT_CHANNEL_DEBUG']
TELEGRAM_BOT_CHANNEL_PROD = config['TELEGRAM']['TELEGRAM_BOT_CHANNEL_PROD']


PUSH_TOKEN = config['PUSHOVER']['PUSH_TOKEN']
PUSH_USER = config['PUSHOVER']['PUSH_USER']

LOCAL_USE = config['CHROMEDRIVER'].getboolean('LOCAL_USE')
HUB_ADDRESS = config['CHROMEDRIVER']['HUB_ADDRESS']

COUNTRY_CODE = 'en-ca'
CODE_TO_CITY_MAP = {'95': "Vancouver", '89': "Calgary", '94': "Toronto", '92': "Ottawa"}

REGEX_CONTINUE = "//a[contains(text(),'Continue')]"
MAX_RETRY = 60


def MY_CONDITION(year, month, day): 
    return int(year) <= 2022 and (int(month) - int(datetime.now().month)) <= 3 
    # No custom condition wanted for the new scheduled date

STEP_TIME = random.randint(1, 3)  # time between steps (interactions): 1 seconds
SLEEP_TIME = random.randint(100, 120)  # recheck time interval: 60 seconds
EXCEPTION_TIME = random.randint(200, 300)  # recheck exception time interval: 5 minutes
RETRY_TIME = random.randint(3600, 7200)  # recheck empty list time interval: 60 minutes

APPOINTMENT_URL = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment"
EXIT = False


def send_notification(channel, msg):
    # Special characters are not allowed
    msg = msg.replace('-', '')
    print(f"Sending msg: {msg}")

    if TELEGRAM_BOT_TOKEN and channel:
        print(f"Sending notification to telegram channel: {channel}")
        url = f"https://api.telegram.org/{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={channel}&parse_mode=MarkdownV2&text={msg}"
        
        try:
            result = requests.post(url)
        except Exception as e:
            print(e.message)

    if PUSH_TOKEN:
        # print(f"Sending notification to pushover: {channel}")
        url = "https://api.pushover.net/1/messages.json"
        data = {
            "token": PUSH_TOKEN,
            "user": PUSH_USER,
            "message": msg
        }
        # Temporarily Disable push over send event due to lack of funding
        # requests.post(url, data)


def get_driver():
    if LOCAL_USE:
        dr = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    else:
        dr = webdriver.Remote(command_executor=HUB_ADDRESS, options=webdriver.ChromeOptions())
    return dr

driver = get_driver()


def login():
    # Bypass reCAPTCHA
    driver.get(f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv")
    time.sleep(STEP_TIME)
    a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    a.click()
    time.sleep(STEP_TIME)

    print("Login start...")
    href = driver.find_element(By.XPATH, '//*[@id="header"]/nav/div[2]/div[1]/ul/li[3]/a')
    href.click()
    time.sleep(STEP_TIME)
    Wait(driver, 60).until(EC.presence_of_element_located((By.NAME, "commit")))

    print("\tclick bounce")
    a = driver.find_element(By.XPATH, '//a[@class="down-arrow bounce"]')
    a.click()
    time.sleep(STEP_TIME)

    do_login_action()


def do_login_action():
    print("\tinput email")
    user = driver.find_element(By.ID, 'user_email')
    user.send_keys(USERNAME)
    time.sleep(random.randint(1, 3))

    print("\tinput pwd")
    pw = driver.find_element(By.ID, 'user_password')
    pw.send_keys(PASSWORD)
    time.sleep(random.randint(1, 3))

    print("\tclick privacy")
    box = driver.find_element(By.CLASS_NAME, 'icheckbox')
    box .click()
    time.sleep(random.randint(1, 3))

    print("\tcommit")
    btn = driver.find_element(By.NAME, 'commit')
    btn.click()
    time.sleep(random.randint(1, 3))

    Wait(driver, 60).until(
        EC.presence_of_element_located((By.XPATH, REGEX_CONTINUE)))
    print("\tlogin successful!")



def get_time(city_code, date):
    time_url = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/times/{city_code}.json?date=%s&appointments[expedite]=false" % date
    driver.get(time_url)
    content = driver.find_element(By.TAG_NAME, 'pre').text
    data = json.loads(content)
    time = data.get("available_times")[-1]
    print(f"Got time successfully! {date} {time}")
    return time


def reschedule(city_code, date):
    global EXIT
    print(f"Starting Reschedule ({date})")

    time = get_time(city_code, date)
    driver.get(APPOINTMENT_URL)

    data = {
        "utf8": driver.find_element_by_name('utf8').get_attribute('value'),
        "authenticity_token": driver.find_element_by_name('authenticity_token').get_attribute('value'),
        "confirmed_limit_message": driver.find_element_by_name('confirmed_limit_message').get_attribute('value'),
        "use_consulate_appointment_capacity": driver.find_element_by_name('use_consulate_appointment_capacity').get_attribute('value'),
        "appointments[consulate_appointment][facility_id]": city_code, # 108
        "appointments[consulate_appointment][date]": date,
        "appointments[consulate_appointment][time]": time,
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36",
        "Referer": APPOINTMENT_URL,
        "Cookie": "_yatri_session=" + driver.get_cookie("_yatri_session")["value"]
    }

    try:
        print(APPOINTMENT_URL)
        print(headers)
        print(data)
        
        r = requests.post(APPOINTMENT_URL, headers=headers, data=data)
        print(r.text)
        if(r.text.find('Successfully Scheduled') != -1):
            msg = f"Rescheduled Successfully! {date} {time}"
            send_notification(TELEGRAM_BOT_CHANNEL_PROD, msg)
            EXIT = True
        else:
            send_notification(TELEGRAM_BOT_CHANNEL_PROD, r.text)
    except Exception as ex: 
        print(ex)
    
    


def is_logged_in():
    content = driver.page_source
    if(content.find("error") != -1):
        return False
    return True


def print_dates(dates):
    print("Available dates:")
    for d in dates:
        print("%s \t business_day: %s" % (d.get('date'), d.get('business_day')))
    print()


last_seen = None


def get_available_date(city_code, dates):
    global last_seen

    def is_earlier(date):
        my_date = datetime.strptime(MY_SCHEDULE_DATE, "%Y-%m-%d")
        new_date = datetime.strptime(date, "%Y-%m-%d")
        result = my_date > new_date
        print(f'Is {my_date} > {new_date}:\t{result}')
        return result

    # print("Checking for an earlier date:")
    for d in dates:
        date = d.get('date')
        # if is_earlier(date) and date != last_seen:
        if date != last_seen:
            year, month, day = date.split('-')
            if(MY_CONDITION(year, month, day)):
                print(f"Found available date for city: {CODE_TO_CITY_MAP[city_code]}: {date}")
                last_seen = date
                if is_earlier(date):
                    print(f"Found earlier date for city: {CODE_TO_CITY_MAP[city_code]}: {date}")
                    return date


def push_notification(channel, city_code, dates):
    msg = "Visa Appointment for City: " + CODE_TO_CITY_MAP[city_code] + " has available dates: "
    for d in dates:
        msg = msg + d.get('date') + '; '
    
    send_notification(channel, msg)


if __name__ == "__main__":
    login()
    retry_count = 0
    
    while 1:
        if retry_count > MAX_RETRY:
            break
        try:
            print("------------------")
            print(datetime.today())
            print(f"Retry count: {retry_count}")
            print()

            empty_list_returned = False
            for city_code in CODE_TO_CITY_MAP:
                print(f"Checking out available dates for city code: {city_code} and city name: {CODE_TO_CITY_MAP[city_code]}")
                date_url = f"https://ais.usvisa-info.com/{COUNTRY_CODE}/niv/schedule/{SCHEDULE_ID}/appointment/days/{city_code}.json?appointments[expedite]=false"
                driver.get(date_url)
                
                if not is_logged_in():
                    login()

                content = driver.find_element(By.TAG_NAME, 'pre').text
                dates = json.loads(content)

                dates =dates[:5]
                print(f"{CODE_TO_CITY_MAP[city_code]}: ")
                print_dates(dates)
                if not dates:
                    empty_list_returned = True
                    send_notification(TELEGRAM_BOT_CHANNEL_DEBUG, f"List is empty for city: {CODE_TO_CITY_MAP[city_code]}")
                    break

                push_notification(TELEGRAM_BOT_CHANNEL_DEBUG, city_code, dates)

                date = get_available_date(city_code, dates)
                if date:
                    print()
                    print(f"Trying to Reschedule for {CODE_TO_CITY_MAP[city_code]}")
                    send_notification(TELEGRAM_BOT_CHANNEL_PROD, f"Earlier Date Found: {CODE_TO_CITY_MAP[city_code]} with date: {date}")
                    # reschedule(city_code, date)

                    print("Available Date notified, exit process for safely")
                    break

                time.sleep(SLEEP_TIME)

            if empty_list_returned:
                # All city list are empty, could be due to too many request
                retry_time = RETRY_TIME
                send_notification(TELEGRAM_BOT_CHANNEL_DEBUG, f"List is empty, sleeping for {retry_time / 60} mins now")
                time.sleep(retry_time)
            else:
                time.sleep(5 * SLEEP_TIME)
        except Exception as ex:
            print(ex)
            retry_count += 1
            send_notification(TELEGRAM_BOT_CHANNEL_DEBUG, f"Exception captured\, {MAX_RETRY - retry_count} retries left")
            time.sleep(EXCEPTION_TIME)

    send_notification(TELEGRAM_BOT_CHANNEL_PROD, "Crashed\! Need HELP\!")
