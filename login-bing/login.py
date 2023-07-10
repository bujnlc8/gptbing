# coding=utf-8

import json
import os
import time
import traceback
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from send_mail import send_mail

DRIVER_PATH = '/bing/chromedriver'

LOGN_URL = 'https://login.live.com/login.srf?wa=wsignin1.0&rpsnv=13&id=264960&wreply=https%3a%2f%2fwww.bing.com%2fsecure%2fPassport.aspx%3fedge_suppress_profile_switch%3d1%26requrl%3dhttps%253a%252f%252fwww.bing.com%252f%253fwlexpsignin%253d1%26sig%3d3D7C913181BC62133D8C83DD80F96371&wp=MBI_SSL&lc=2052&CSRFToken=8af3d639-be36-45c6-a5b6-0c50b7d74e12&aadredir=1'

BING_ACCOUNT_LIST = json.loads(os.environ.get('BING_ACCOUNT_LIST', '[]'))

MAIL_SENDER = os.environ.get('MAIL_SENDER')
MAIL_SENDER_PASSWD = os.environ.get('MAIL_SENDER_PASSWD')
MAIL_RECEIVER = os.environ.get('MAIL_RECEIVER')
MAIL_RECEIVER = MAIL_RECEIVER or MAIL_SENDER

UPDATE_TIME = int(os.environ.get('UPDATE_TIME', 10 * 24 * 3600))


def login(index, user_name, passwd):
    print('[%s] login: %s' % (datetime.now(), user_name))
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = uc.Chrome(
        options=options,
        driver_executable_path=DRIVER_PATH,
        version_main=114,
    )
    driver.get(LOGN_URL)
    emali_input = WebDriverWait(driver, 90).until(EC.presence_of_element_located((By.NAME, 'loginfmt')))
    emali_input.send_keys(user_name)
    next_bt = driver.find_element(By.ID, 'idSIButton9')
    next_bt.click()
    time.sleep(30)
    passwd_input = WebDriverWait(driver, 90).until(EC.presence_of_element_located((By.ID, 'i0118')))
    passwd_input.send_keys(passwd)
    submit_bt = WebDriverWait(driver, 90).until(EC.presence_of_element_located((By.ID, 'idSIButton9')))
    submit_bt.click()
    time.sleep(30)
    submit_bt = driver.find_element(By.ID, 'idSIButton9')
    submit_bt.click()
    # wait for redirect to www.bing.com
    time.sleep(60)
    driver.get('https://www.bing.com')
    time.sleep(60)
    cookies = driver.get_cookies()
    with open('/bing/cookies/cookie{}.json'.format(index), 'w') as f:
        json.dump(cookies, f)
        f.flush()
    driver.close()
    print('[%s] %s login success!' % (datetime.now(), user_name))


def should_update(file_path):
    if not os.path.exists(file_path):
        return True
    mtime = os.path.getmtime(file_path)
    if (time.time() - mtime) > (UPDATE_TIME - 3600):
        return True


if __name__ == '__main__':
    err = ''
    success = []
    for index in range(len(BING_ACCOUNT_LIST)):
        user = BING_ACCOUNT_LIST[index]['user']
        try:
            file_path = '/bing/cookies/cookie{}.json'.format(index)
            if not should_update(file_path):
                print('[%s] %s 无需更新' % (datetime.now(), user))
                continue
            login(index, user, BING_ACCOUNT_LIST[index]['password'])
            success.append(user)
            time.sleep(60)
        except Exception as e:
            err += '刷新 {} 遇到异常: \n{}\n'.format(user, traceback.format_exc())
    msg = ''
    if success:
        msg = '成功刷新以下账号的cookie: \n' + '\n'.join(success) + '\n'
    if err:
        msg += err
    if msg:
        send_mail(MAIL_SENDER, MAIL_SENDER_PASSWD, MAIL_RECEIVER, 'Bing Cookie刷新', msg)
