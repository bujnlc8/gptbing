# coding=utf-8
import json
import os
import random
import re
import string
import pickle

import httpx


class Chatbot:
    """
    A class to interact with Google Bard.
    Parameters
        session_id: str
            The __Secure-1PSID cookie.
        proxy: str
        timeout: int
            Request timeout in seconds.
    """

    __slots__ = [
        'headers',
        '_reqid',
        'SNlM0e',
        'conversation_id',
        'response_id',
        'choice_id',
        'proxy',
        'session_id',
        'session',
        'timeout',
        'file_path',
    ]

    def __init__(
        self,
        session_id: str = '',
        proxy: dict = None,
        timeout: int = 60,
        file_path: str = '',
    ):
        headers = {
            'Host': 'bard.google.com',
            'X-Same-Domain': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',  # noqa
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
            'Origin': 'https://bard.google.com',
            'Referer': 'https://bard.google.com/',
        }
        session_id = session_id or os.environ.get('BARD_SESSION')
        proxy = proxy or os.environ.get('https_proxy')
        self._reqid = int(''.join(random.choices(string.digits, k=4)))
        self.proxy = proxy
        self.conversation_id = ''
        self.response_id = ''
        self.choice_id = ''
        self.session_id = session_id
        self.session = httpx.AsyncClient(proxies=self.proxy)
        self.session.headers = headers
        self.session.cookies.set('__Secure-1PSID', session_id)
        self.timeout = timeout
        self.file_path = file_path

    @classmethod
    async def create(
        cls,
        session_id: str = '',
        proxy: dict = None,
        timeout: int = 60,
        file_path: str = '',
    ) -> 'Chatbot':
        instance = cls(session_id, proxy, timeout, file_path)
        if not await instance.load_conversation():
            instance.SNlM0e = await instance.__get_snlm0e()
        return instance

    async def save_conversation(self):
        conversation_detail = {
            '_reqid': self._reqid,
            'conversation_id': self.conversation_id,
            'response_id': self.response_id,
            'choice_id': self.choice_id,
            'SNlM0e': self.SNlM0e,
        }
        with open(self.file_path, 'wb') as f:
            pickle.dump(conversation_detail, f)

    async def load_conversation(self) -> bool:
        """
        Loads a conversation from history file. Returns whether the conversation was found.
        """
        conversation = {}
        if not os.path.exists(self.file_path):
            return False
        with open(self.file_path, 'rb') as f:
            conversation = pickle.load(f)
        self._reqid = conversation['_reqid']
        self.conversation_id = conversation['conversation_id']
        self.response_id = conversation['response_id']
        self.choice_id = conversation['choice_id']
        self.SNlM0e = conversation['SNlM0e']
        return True

    async def __get_snlm0e(self):
        # Find 'SNlM0e':'<ID>'
        if not self.session_id or self.session_id[-1] != '.':
            raise Exception('__Secure-1PSID value must end with a single dot. Enter correct __Secure-1PSID value.', )
        resp = await self.session.get(
            'https://bard.google.com/',
            timeout=self.timeout,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            raise Exception(f'Response code not 200. Response Status is {resp.status_code}', )
        SNlM0e = re.search(r'"SNlM0e":"(.*?)"', resp.text)
        if not SNlM0e:
            raise Exception('SNlM0e value not found in response. Check __Secure-1PSID value.', )
        return SNlM0e.group(1)

    async def ask(self, message: str) -> dict:
        """
        Send a message to Google Bard and return the response.
        :param message: The message to send to Google Bard.
        :return: A dict containing the response from Google Bard.
        """
        # url params
        params = {
            'bl': 'boq_assistant-bard-web-server_20230606.12_p0',
            '_reqid': str(self._reqid),
            'rt': 'c',
        }

        # message arr -> data['f.req']. Message is double json stringified
        message_struct = [
            [message],
            None,
            [self.conversation_id, self.response_id, self.choice_id],
        ]
        data = {
            'f.req': json.dumps([None, json.dumps(message_struct)]),
            'at': self.SNlM0e,
        }
        resp = await self.session.post(
            'https://bard.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate',
            params=params,
            data=data,
            timeout=self.timeout,
        )
        chat_data = json.loads(resp.content.splitlines()[3])[0][2]
        if not chat_data:
            return {
                'content': f'Google Bard encountered an error: {resp.content}.'
            }
        json_chat_data = json.loads(chat_data)
        images = []
        if len(json_chat_data) >= 3:
            if len(json_chat_data[4][0]) >= 4:
                if json_chat_data[4][0][4]:
                    for img in json_chat_data[4][0][4]:
                        images.append(img[0][0][0])
        results = {
            'content': json_chat_data[0][0],
            'conversation_id': json_chat_data[1][0],
            'response_id': json_chat_data[1][1],
            'factualityQueries': json_chat_data[3],
            'textQuery': json_chat_data[2][0] if json_chat_data[2] is not None else '',
            'choices': [{
                'id': i[0],
                'content': i[1]
            } for i in json_chat_data[4]],
            'images': images,
        }
        self.conversation_id = results['conversation_id']
        self.response_id = results['response_id']
        self.choice_id = results['choices'][0]['id']
        self._reqid += 100000
        return results
