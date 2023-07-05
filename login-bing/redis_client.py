# coding=utf-8

import os
import traceback

import redis

REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWD = os.environ.get('REDIS_PASSWD', '123456')
REDIS_DB = int(os.environ.get('REDIS_DB', 0))


class RedisClient:

    CAPTCHA = 'bing:captcha'

    def __init__(self, client=None) -> None:
        self.redis_client = client
        if client is None:
            self.init()

    def init(self):
        if self.redis_client is not None:
            return
        pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWD)
        self.redis_client = redis.Redis(connection_pool=pool)

    def subscribe_captcha(self):
        pub = self.redis_client.pubsub()
        pub.subscribe(self.CAPTCHA)
        while True:
            try:
                for msg in pub.listen():
                    if msg['type'] != 'message':
                        continue
                    yield msg['data'].decode()
            except:
                traceback.print_exc()


redis_client = RedisClient()
