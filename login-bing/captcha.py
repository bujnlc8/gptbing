# coding=utf-8

import datetime
import json
import sys
import time
import traceback

import undetected_chromedriver as uc
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from undetected_chromedriver.patcher import random

from redis_client import redis_client

CHAT_URL = 'https://www.bing.com/search?form=MY0291&OCID=MY0291&q=Bing+AI&showconv=1'

DRIVER_PATH = '/bing/chromedriver'

COOKIE_PREFIX = '/bing/cookies/'

JS = "return document.querySelector('.cib-serp-main').shadowRoot.querySelector('#cib-action-bar-main').shadowRoot.querySelector('cib-text-input').shadowRoot.querySelector('textarea')"


def get_textarea(driver):
    try:
        return driver.execute_script(JS)
    except:
        pass


def solve_captcha(cookie_path):
    cookies = []
    with open(cookie_path, 'r') as f:
        cookies = json.load(f)
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-application-cache')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--load-extension=/bing/extension')
    options.add_argument('--lang=en')
    options.add_argument(
        '--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.67'
    )
    driver = uc.Chrome(
        options=options,
        driver_executable_path=DRIVER_PATH,
        version_main=114,
    )
    driver.get('https://www.bing.com')
    driver.delete_all_cookies()
    time.sleep(random.randint(15, 20))
    for cookie in cookies:
        driver.add_cookie({
            'name': cookie['name'],
            'value': cookie['value'],
        })
    try:
        driver.get(CHAT_URL)
        time.sleep(random.randint(60, 120))
        driver.save_screenshot('/bing/shot/1.png')
        search_box = get_textarea(driver)
        if not search_box:
            driver.get(CHAT_URL)
            time.sleep(random.randint(60, 120))
            driver.save_screenshot('/bing/shot/2.png')
            search_box = get_textarea(driver)
        if not search_box:
            try:
                bt = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'b-scopeListItem-conv')))
                bt.click()
                time.sleep(random.randint(60, 90))
                driver.save_screenshot('/bing/shot/3.png')
                search_box = get_textarea(driver)
            except:
                pass
        if not search_box:
            raise Exception('not found search_box')
        search_box.send_keys('hello')
        time.sleep(random.randint(5, 10))
        search_box.send_keys(Keys.ENTER)
        time.sleep(random.randint(10, 20))
        driver.save_screenshot('/bing/shot/4.png')
        print('success', datetime.datetime.now(), cookie_path)
    except Exception:
        traceback.print_exc()
        driver.save_screenshot('/bing/shot/5.png')
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
