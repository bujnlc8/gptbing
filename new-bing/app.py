# coding=utf-8

import os
import re
import threading

import requests
from sanic import Sanic
from sanic.response import json

from EdgeGPT import Chatbot, ConversationStyle

APPID = os.environ.get('WXAPPID')
APPSECRET = os.environ.get('WXAPPSECRET')
WX_URL = 'https://api.weixin.qq.com/sns/jscode2session?appid=%s&secret=%s&js_code=%s&grant_type=authorization_code'
# 备用cookie
COOKIE = os.environ.get('COOKIE_FILE', '')
BAK_COOKIE = os.environ.get('COOKIE_FILE1', '')
BAK_COOKIE1 = os.environ.get('COOKIE_FILE2', '')

LOCK = threading.Lock()


def reset_cookie():
    if not LOCK.acquire(blocking=False):
        return
    cookie = os.environ.get('COOKIE_FILE')
    if cookie == COOKIE:
        if BAK_COOKIE:
            os.environ['COOKIE_FILE'] = BAK_COOKIE
    elif cookie == BAK_COOKIE:
        if BAK_COOKIE1:
            os.environ['COOKIE_FILE'] = BAK_COOKIE1
    elif cookie == BAK_COOKIE1:
        os.environ['COOKIE_FILE'] = COOKIE
    LOCK.release()


app = Sanic('new-bing')
app.config.REQUEST_TIMEOUT = 900
app.config.RESPONSE_TIMEOUT = 900
bots = {}


def get_bot(sid):
    if sid in bots:
        return bots[sid]
    bot = Chatbot()
    bots[sid] = bot
    return bot


async def do_chat(request):
    return await get_bot(request.json.get('sid')).ask(
        request.json.get('q'), conversation_style=ConversationStyle.balanced
    )


@app.post('/chat')
async def chat(request):
    res = await do_chat(request)
    auto_reset = request.json.get('auto_reset', '')
    sid = request.json.get('sid')
    status = res['item']['result']['value']
    if status == 'Throttled':
        reset_cookie()
        await get_bot(sid).reset()
        res = await do_chat(request)
        status = res['item']['result']['value']
    text = ''
    suggests = []
    if status == 'Success':
        item = res['item']['messages']
        if len(item) >= 2:
            text = item[1]['text']
            if re.search(r'\[\^\d+\^\]', text):
                text = item[1]['adaptiveCards'][0]['body'][0]['text']
            text = re.sub(r'\[\^\d+\^\]', '', text)
            suggests = [x['text'] for x in item[1]['suggestedResponses']] if 'suggestedResponses' in item[1] else []
        else:
            text = '抱歉，未搜索到结果，请重试。'
            suggests = [request.json.get('q')]
    msg = res['item']['result']['message'] if 'message' in res['item']['result'] else ''
    # 自动reset
    if auto_reset and ('New topic' in text or 'has expired' in msg):
        await get_bot(sid).reset()
    return json({
        'data': {
            'status': status,
            'text': text,
            'suggests': suggests,
            'message': msg,
        },
        'cookie': os.environ.get('COOKIE_FILE')
    })


@app.route('/reset')
async def reset(request):
    await get_bot(request.args.get('sid')).reset()
    return json({'data': ''})


@app.route('/openid')
async def openid(request):
    code = request.args.get('code')
    url = WX_URL % (APPID, APPSECRET, code)
    return json({'data': requests.get(url).json()})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, workers=4)
