# coding=utf-8

import json
import os

import redis

REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_PASSWD = os.environ.get('REDIS_PASSWD', '123456')
REDIS_DB = int(os.environ.get('REDIS_DB', 0))


class ConversationCtr:

    LAST_SYNC_TIME_KEY = 'bing:last_sync_time:%s'
    CONVERSATION_LIST_KEY = 'bing:conversation_list:%s'
    OPENAI_WHITE_LIST_KEY = 'bing:openai_white_list'

    def __init__(self, client=None) -> None:
        self.redis_client = client
        if client is None:
            self.init()

    def init(self):
        if self.redis_client is not None:
            return
        pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, password=REDIS_PASSWD)
        self.redis_client = redis.Redis(connection_pool=pool)

    def get_last_sync_time(self, sid):
        key = self.LAST_SYNC_TIME_KEY % sid
        v = self.redis_client.get(key)
        return v.decode() if v else ''

    def get_by_page(self, sid, page=1, size=20):
        offset = size * (page - 1) if page > 0 else 0
        key = self.CONVERSATION_LIST_KEY % sid
        return [json.loads(x) for x in self.redis_client.lrange(key, offset, offset + size - 1)]

    def save(self, sid, conversations):
        _last_sync_time = self.get_last_sync_time(sid)
        conversations = [x for x in conversations if x['dt'] > _last_sync_time]
        if len(conversations) <= 0:
            return
        key = self.CONVERSATION_LIST_KEY % sid
        self.redis_client.lpush(key, *[json.dumps(x) for x in conversations])
        self.redis_client.set(self.LAST_SYNC_TIME_KEY % sid, conversations[-1]['dt'])

    def delete(self, sid, conversation):
        key = self.CONVERSATION_LIST_KEY % sid
        self.redis_client.lrem(key, 0, json.dumps(conversation))

    def delete_all(self, sid):
        key = self.CONVERSATION_LIST_KEY % sid
        self.redis_client.delete(key)

    def get_openai_whitelist(self):
        return self.redis_client.lrange(self.OPENAI_WHITE_LIST_KEY, 0, 10000)


conversation_ctr = ConversationCtr()