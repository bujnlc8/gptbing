# coding=utf-8

import json as raw_json
import os
import re
import threading
from collections import defaultdict
from datetime import datetime, timedelta

import openai
import requests
from sanic import Sanic
from sanic.log import logger
from sanic.response import json

from conversation_ctr import conversation_ctr
from EdgeGPT import Chatbot, ConversationStyle

APPID = os.environ.get('WXAPPID')
APPSECRET = os.environ.get('WXAPPSECRET')
WX_URL = 'https://api.weixin.qq.com/sns/jscode2session?appid=%s&secret=%s&js_code=%s&grant_type=authorization_code'

# cookie列表, 如果有此环境变量，优先使用
COOKIE_FILES = raw_json.loads(os.environ.get('COOKIE_FILES', '[]'))
if COOKIE_FILES:
    os.environ['COOKIE_FILE'] = COOKIE_FILES[0]
else:
    COOKIE = os.environ.get('COOKIE_FILE', '')
    if not COOKIE:
        raise ValueError('COOKIE_FILE环境变量为空')
    BAK_COOKIE = os.environ.get('COOKIE_FILE1', COOKIE)
    BAK_COOKIE1 = os.environ.get('COOKIE_FILE2', COOKIE)
    BAK_COOKIE2 = os.environ.get('COOKIE_FILE3', COOKIE)

LOCK = threading.Lock()
bots = {}

app = Sanic('new-bing')
app.config.REQUEST_TIMEOUT = 900
app.config.RESPONSE_TIMEOUT = 900
app.config.WEBSOCKET_PING_INTERVAL = 15
app.config.WEBSOCKET_PING_TIMEOUT = 30

# openai conversation
OPENAI_CONVERSATION = defaultdict(lambda: [])


def reset_cookie():
    if not LOCK.acquire(blocking=False):
        return
    cookie = os.environ.get('COOKIE_FILE')
    if COOKIE_FILES:
        os.environ['COOKIE_FILE'] = COOKIE_FILES[(COOKIE_FILES.index(cookie) + 1) % len(COOKIE_FILES)]
    else:
        if cookie == COOKIE:
            os.environ['COOKIE_FILE'] = BAK_COOKIE
        elif cookie == BAK_COOKIE:
            os.environ['COOKIE_FILE'] = BAK_COOKIE1
        elif cookie == BAK_COOKIE1:
            os.environ['COOKIE_FILE'] = BAK_COOKIE2
        elif cookie == BAK_COOKIE2:
            os.environ['COOKIE_FILE'] = COOKIE
    LOCK.release()


def make_response_data(status, text, suggests, message, num_in_conversation=-1):
    return {
        'data': {
            'status': status,
            'text': text,
            'suggests': suggests,
            'message': message,
            'num_in_conversation': num_in_conversation,
        },
        'cookie': os.environ.get('COOKIE_FILE'),
    }


@app.websocket('/chat')
async def ws_chat(_, ws):
    while True:
        try:
            data = raw_json.loads(await ws.recv())
            logger.info('[bing] Websocket receive data: %s', data)
            sid = data['sid']
            q = data['q']
            index = 0
            async for response in get_bot(sid).ask_stream(q, conversation_style=ConversationStyle.creative):
                final, res = response
                if final:
                    processed_data = await process_data(res, q, sid, auto_reset=1)
                    if processed_data['data']['status'] == 'Throttled':
                        reset_cookie()
                        await reset_conversation(sid)
                        processed_data['data']['suggests'].append(q)
                    await ws.send(raw_json.dumps({
                        'final': final,
                        'data': processed_data
                    }))
                else:
                    index += 1
                    if index % 3 == 1:
                        await ws.send(raw_json.dumps({
                            'final': final,
                            'data': res
                        }))
        except Exception as e:
            logger.error(e)
            await ws.send(raw_json.dumps({
                'final': True,
                'data': make_response_data('Error', str(e), [], str(e))
            }))


def get_bot(sid):
    if sid in bots:
        record = bots[sid]
        if record['expired'] > datetime.now():
            return record['bot']
    bot = Chatbot()
    bots[sid] = {
        'bot': bot,
        'expired': datetime.now() + timedelta(hours=5, minutes=55),  # 会话有效期为6小时
    }
    return bot


async def reset_conversation(sid):
    await get_bot(sid).reset()
    bots[sid]['expired'] = datetime.now() + timedelta(hours=5, minutes=55)


async def do_chat(request):
    logger.info('[bing] Http request payload: %s', request.json)
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
    msg = res['item']['result']['message'] if 'message' in res['item']['result'] else ''
    if auto_reset and ('New topic' in text or 'has expired' in msg):
        await reset_conversation(sid)
    return make_response_data(
        status, text, suggests, msg,
        res['item']['throttling']['numUserMessagesInConversation'] if 'throttling' in res['item'] else -1
    )


@app.post('/chat')
async def chat(request):
    res = await do_chat(request)
    auto_reset = request.json.get('auto_reset', '')
    sid = request.json.get('sid')
    data = await process_data(res, request.json.get('q'), sid, auto_reset)
    if data['data']['status'] == 'Throttled':
        reset_cookie()
        await reset_conversation(sid)
        res = await do_chat(request)
        data = await process_data(res, request.json.get('q'), sid, auto_reset)
    return json(data)


@app.route('/reset')
async def reset(request):
    await reset_conversation(request.args.get('sid'))
    return json({'data': ''})


@app.route('/openid')
async def openid(request):
    code = request.args.get('code')
    url = WX_URL % (APPID, APPSECRET, code)
    return json({'data': requests.get(url).json()})


# #########################################以下是openid接口##################################


@app.websocket('/ws_openai_chat')
async def ws_openai_chat(_, ws):
    while True:
        try:
            data = raw_json.loads(await ws.recv())
            logger.info('[openai] Websocket receive data: %s', data)
            sid = data['sid']
            q = data['q']
            # 保存30个对话
            history_conversation = OPENAI_CONVERSATION[sid][-30:]
            history_conversation.append({
                'role': 'user',
                'content': q,
            })
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=history_conversation,
                temperature=1.2,
                stream=True,
            )
            chunks = []
            index = 0
            for chunk in response:
                chunk_message = chunk['choices'][0]['delta']
                if chunk_message:
                    if 'content' in chunk_message:
                        chunks.append(chunk_message['content'])
                        index += 1
                    if index % 5 == 1:
                        await ws.send(
                            raw_json.dumps({
                                'final': False,
                                'data': make_response_data('Success', ''.join(chunks), [], '')
                            })
                        )
                else:
                    OPENAI_CONVERSATION[sid].append({
                        'role': 'assistant',
                        'content': ''.join(chunks)
                    })
                    await ws.send(
                        raw_json.dumps({
                            'final': True,
                            'data': make_response_data('Success', ''.join(chunks), [], '')
                        })
                    )
        except Exception as e:
            logger.error(e)
            await ws.send(raw_json.dumps({
                'final': True,
                'data': make_response_data('Error', str(e), [], str(e))
            }))


@app.post('/openai_chat')
async def openai_chat(request):
    try:
        logger.info('[openai] Http request payload: %s', request.json)
        sid = request.json.get('sid')
        q = request.json.get('q')
        history_conversation = OPENAI_CONVERSATION[sid][-30:]
        history_conversation.append({
            'role': 'user',
            'content': q,
        })
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=history_conversation,
            temperature=1.2,
            stream=True,
        )
        chunks = []
        for chunk in response:
            chunk_message = chunk['choices'][0]['delta']
            if chunk_message:
                if 'content' in chunk_message:
                    chunks.append(chunk_message['content'])
            else:
                OPENAI_CONVERSATION[sid].append({
                    'role': 'assistant',
                    'content': ''.join(chunks)
                })
                return json(make_response_data('Success', ''.join(chunks), [], ''))
    except Exception as e:
        logger.error(e)
        return json(make_response_data('Error', str(e), [], str(e)))


@app.route('/last_sync_time')
async def last_sync_time(request):
    return json({'last_sync_time': conversation_ctr.get_last_sync_time(request.args.get('sid'))})


@app.post('/save')
async def save(request):
    conversation_ctr.save(request.json.get('sid'), request.json.get('conversations'))
    return json({})


@app.route('/query')
async def query(request):
    data = conversation_ctr.get_by_page(
        request.args.get('sid'), int(request.args.get('page', '1')), int(request.args.get('size', '20'))
    )
    return json({'data': data})


@app.post('/delete')
async def delete(request):
    conversation_ctr.delete(request.json.get('sid'), request.json.get('conversation'))
    return json({})


@app.post('/delete_all')
async def delete_all(request):
    conversation_ctr.delete_all(request.json.get('sid'))
    return json({})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
