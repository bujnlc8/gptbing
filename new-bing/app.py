# coding=utf-8

import json as raw_json
import logging
import os
import re
import threading

import requests
from sanic import Sanic
from sanic.response import json

from EdgeGPT import Chatbot, ConversationStyle

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

APPID = os.environ.get('WXAPPID')
APPSECRET = os.environ.get('WXAPPSECRET')
WX_URL = 'https://api.weixin.qq.com/sns/jscode2session?appid=%s&secret=%s&js_code=%s&grant_type=authorization_code'
COOKIE = os.environ.get('COOKIE_FILE', '')
# 备用cookie
BAK_COOKIE = os.environ.get('COOKIE_FILE1', '')
BAK_COOKIE1 = os.environ.get('COOKIE_FILE2', '')

LOCK = threading.Lock()
BOT_LOCK = threading.Lock()
bots = {}

app = Sanic('new-bing')
app.config.REQUEST_TIMEOUT = 900
app.config.RESPONSE_TIMEOUT = 900
app.config.WEBSOCKET_PING_INTERVAL = 15
app.config.WEBSOCKET_PING_TIMEOUT = 15


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


@app.websocket('/chat')
async def ws_chat(request, ws):
    while True:
        data = raw_json.loads(await ws.recv())
        logger.warn('Receive data: %s', data)
        sid = data['sid']
        q = data['q']
        async for response in get_bot(sid).ask_stream(q, conversation_style=ConversationStyle.creative):
            final, res = response
            if final:
                processed_data = await process_data(res, q, sid, auto_reset=1)
                if processed_data['data']['status'] == 'Throttled':
                    reset_cookie()
                    await get_bot(sid).reset()
                    processed_data['data']['suggests'].append(q)
                await ws.send(raw_json.dumps({
                    'final': final,
                    'data': processed_data
                }))
            else:
                await ws.send(raw_json.dumps({
                    'final': final,
                    'data': res
                }))


def get_bot(sid):
    BOT_LOCK.acquire(timeout=5)
    if sid in bots:
        BOT_LOCK.release()
        return bots[sid]
    bot = Chatbot()
    bots[sid] = bot
    BOT_LOCK.release()
    return bot


async def do_chat(request):
    logger.warn('Request payload: %s', request.json)
    return await get_bot(request.json.get('sid')).ask(
        request.json.get('q'), conversation_style=ConversationStyle.creative
    )


async def process_data(res, q, sid, auto_reset=None):
    text = ''
    suggests = []
    status = res['item']['result']['value']
    if status == 'Success':
        item = res['item']['messages']
        if len(item) >= 2:
            if 'adaptiveCards' in item[1]:
                try:
                    text = item[1]['adaptiveCards'][0]['body'][0]['text']
                except KeyError:
                    pass
            if not text:
                if 'text' not in item[1]:
                    text = '响应异常'
                    logger.error('响应异常：%s', res)
                else:
                    text = item[1]['text']
            text = re.sub(r'\[\^\d+\^\]', '', text)
            suggests = [x['text'] for x in item[1]['suggestedResponses']] if 'suggestedResponses' in item[1] else []
        else:
            text = '抱歉，未搜索到结果。'
            logger.error('响应异常：%s', res)
            suggests = [q]
            if res['type'] == 2:
                await get_bot(sid).reset()
                text += '\n\n已结束本轮对话。'
    msg = res['item']['result']['message'] if 'message' in res['item']['result'] else ''
    if auto_reset and ('New topic' in text or 'has expired' in msg):
        await get_bot(sid).reset()
    return {
        'data': {
            'status': status,
            'text': text,
            'suggests': suggests,
            'message': msg,
            'num_in_conversation': res['item']['throttling']['numUserMessagesInConversation']
            if 'throttling' in res['item'] else -1,
        },
        'cookie': os.environ.get('COOKIE_FILE'),
    }


@app.post('/chat')
async def chat(request):
    res = await do_chat(request)
    auto_reset = request.json.get('auto_reset', '')
    sid = request.json.get('sid')
    data = await process_data(res, request.json.get('q'), sid, auto_reset)
    if data['data']['status'] == 'Throttled':
        reset_cookie()
        await get_bot(sid).reset()
        res = await do_chat(request)
        data = await process_data(res, request.json.get('q'), sid, auto_reset)
    return json(data)


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
    app.run(host='0.0.0.0', port=8000)
