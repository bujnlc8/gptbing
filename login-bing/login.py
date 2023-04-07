# coding=utf-8

import json
import os
import time
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from send_mail import send_mail

LOGN_URL = 'https://login.live.com/login.srf?wa=wsignin1.0&rpsnv=13&id=264960&wreply=https%3a%2f%2fwww.bing.com%2fsecure%2fPassport.aspx%3fedge_suppress_profile_switch%3d1%26requrl%3dhttps%253a%252f%252fwww.bing.com%252f%253fwlexpsignin%253d1%26sig%3d3D7C913181BC62133D8C83DD80F96371&wp=MBI_SSL&lc=2052&CSRFToken=8af3d639-be36-45c6-a5b6-0c50b7d74e12&aadredir=1'

BING_ACCOUNT_LIST = json.loads(os.environ.get('BING_ACCOUNT_LIST', '[]'))

MAIL_SENDER = os.environ.get('MAIL_SENDER')
MAIL_SENDER_PASSWD = os.environ.get('MAIL_SENDER_PASSWD')
MAIL_RECEIVER = os.environ.get('MAIL_RECEIVER')
MAIL_RECEIVER = MAIL_RECEIVER or MAIL_SENDER


def login(index, user_name, passwd):
    print('[%s] login: %s' % (datetime.now(), user_name))
    options = Options()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(options=options, executable_path='/bing/chromedriver')
    driver.get(LOGN_URL)
    emali_input = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.NAME, 'loginfmt')))
    emali_input.send_keys(user_name)
    next_bt = driver.find_element(By.ID, 'idSIButton9')
    next_bt.click()
    time.sleep(30)
    passwd_input = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'i0118')))
    passwd_input.send_keys(passwd)
    submit_bt = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'idSIButton9')))
    submit_bt.click()
    time.sleep(30)
    submit_bt = driver.find_element(By.ID, 'idSIButton9')
    submit_bt.click()
    # wait for redirect to www.bing.com
    time.sleep(30)
    cookies = driver.get_cookies()
    with open('/bing/cookies/cookie{}.json'.format(index), 'w') as f:
        json.dump(cookies, f)
        f.flush()
    print('[%s] %s login success!' % (datetime.now(), user_name))


if __name__ == '__main__':
    try:
        for index in range(len(BING_ACCOUNT_LIST)):
            login(index, BING_ACCOUNT_LIST[index]['user'], BING_ACCOUNT_LIST[index]['password'])
        send_mail(
            MAIL_SENDER,
            MAIL_SENDER_PASSWD,
            MAIL_RECEIVER,
            'Bing Cookie刷新',
            '成功刷新以下账号的cookie: \n' + '\n'.join([x['user'] for x in BING_ACCOUNT_LIST]),
        )
    except Exception as e:
        send_mail(
            MAIL_SENDER,
            MAIL_SENDER_PASSWD,
            MAIL_RECEIVER,
            'Bing Cookie刷新',
            '刷新遇到异常: \n' + traceback.format_exc(),
        )