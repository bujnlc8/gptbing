# coding=utf-8

import datetime
import json
import os
import sys
import time
import traceback

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from redis_client import redis_client

BING_ACCOUNT_LIST = json.loads(os.environ.get('BING_ACCOUNT_LIST', '[]'))

CAPTCHA_URL = 'https://www.bing.com/turing/captcha/challenge'

DRIVER_PATH = '/bing/chromedriver'

COOKIE_PREFIX = '/bing/cookies/'


def solve_captcha(cookie_path):
    cookies = []
    with open(cookie_path, 'r') as f:
        cookies = json.load(f)
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = uc.Chrome(
        options=options,
        driver_executable_path=DRIVER_PATH,
        version_main=112,
    )
    driver.get('https://www.bing.com')
    driver.delete_all_cookies()
    time.sleep(5)
    for cookie in cookies:
        driver.add_cookie({
            'name': cookie['name'],
            'value': cookie['value'],
            'domain': cookie['domain'],
        })
    try:
        driver.get(CAPTCHA_URL)
        driver.switch_to.frame(0)
        try_times = 20
        while try_times:
            try_times -= 1
            success = WebDriverWait(driver, 180).until(EC.presence_of_element_located((By.ID, 'success')))
            if success and success.is_displayed():
                print('[Success]', datetime.datetime.now(), cookie_path)
                break
            time.sleep(15)
            if not try_times:
                raise Exception('[Failed]', cookie_path)
            if try_times % 6 == 0:
                driver.get(CAPTCHA_URL)
                time.sleep(15)
                driver.switch_to.frame(0)
        driver.get('https://www.bing.com')
        time.sleep(60)
        cookies = driver.get_cookies()
        if cookies:
            with open(cookie_path, 'w') as f:
                json.dump(cookies, f)
                f.flush()
    except Exception:
        print(driver.get_screenshot_as_base64())
    finally:
        driver.close()


if __name__ == '__main__':
    while True:
        try:
            for cookie_path in redis_client.subscribe_captcha():
                try:
                    print('receive: ', datetime.datetime.now(), cookie_path)
                    sys.stdout.flush()
                    solve_captcha(COOKIE_PREFIX + cookie_path)
                    sys.stdout.flush()
                except:
                    traceback.print_exc()
        except:
            traceback.print_exc()
