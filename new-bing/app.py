# coding=utf-8

import asyncio
import json as raw_json
import os
import re
import traceback
from collections import defaultdict
from datetime import datetime, timedelta

import openai
import aiohttp
import requests
import tiktoken
import pickle
from BingImageCreator import async_image_gen
from common import DAY_LIMIT, FORBIDDEN_TIP, INTERNAL_ERROR, NO_ACCESS, OVER_DAY_LIMIT, SERVICE_NOT_AVALIABLE
from conversation_ctr import conversation_ctr
from dfa import dfa
from EdgeGPT import Chatbot, ConversationStyle
from logger import logger
from sanic import Sanic
from sanic.response import json
from send_mail import send_mail

APPID = os.environ.get('WXAPPID')
APPSECRET = os.environ.get('WXAPPSECRET')
WX_URL = 'https://api.weixin.qq.com/sns/jscode2session?appid=%s&secret=%s&js_code=%s&grant_type=authorization_code'

# cookie列表
COOKIE_FILES = raw_json.loads(os.environ.get('COOKIE_FILES', '[]'))
if not COOKIE_FILES:
    raise ValueError('COOKIE_FILES环境变量为空')

app = Sanic('new-bing')
app.config.REQUEST_TIMEOUT = 900
app.config.RESPONSE_TIMEOUT = 900
app.config.WEBSOCKET_PING_INTERVAL = 10
app.config.WEBSOCKET_PING_TIMEOUT = 60

bots = {}

# openai conversation
OPENAI_CONVERSATION = defaultdict(lambda: [])

OPENAI_DEFAULT_PROMPT = {
    'role': 'system',
    'content': "You are ChatGPT, a large language model trained by OpenAI. Follow the user's instructions carefully. Respond using markdown."  # type: ignore
}

HIDDEN_TEXTS = [
    '实在抱歉，我现在无法回答这个问题。',
    '嗯……对于这个问题很抱歉',
    'try a different topic.',
]


def check_hidden(text):
    if not text:
        return False
    for x in HIDDEN_TEXTS:
        if x in text:
            return True
    return False


def get_cookie_file(sid, cookie_files, reset=False):
    # 优先获取最后一个
    if not reset and show_chatgpt(sid):
        return cookie_files[-1]
    # 根据sid相加取余算出一个数
    total_cookie_num = len(cookie_files) - 1
    return cookie_files[(
        sum([ord(x)
             for x in sid.replace('_', '').replace('-', '')[10:]]) + conversation_ctr.get_switch_cookie_step(sid)
    ) % total_cookie_num]


def get_bot(sid, cookie_path=None):
    if sid in bots:
        record = bots[sid]
        if record['expired'] > datetime.now():
            bot = record['bot']
            if cookie_path:
                bot.cookie_path = cookie_path
            return bot
    cookie_path = cookie_path or get_cookie_file(sid, COOKIE_FILES)
    logger.info('[BotCookie] sid: %s, cookie_path: %s', sid, cookie_path)
    try:
        # 尝试恢复会话
        file = '/sanic/sessions/{}'.format(sid)
        with open(file, 'rb') as f:
            bot = Chatbot(cookie_path=cookie_path, request=pickle.load(f))
        os.remove(file)
        logger.info('Reload %s session success.', sid)
    except Exception:
        logger.error('Reload %s session error.', sid, exc_info=True)
        bot = Chatbot(cookie_path=cookie_path)
    bots[sid] = {
        'bot': bot,
        'expired': datetime.now() + timedelta(days=89, hours=23, minutes=55),  # 会话有效期为90天
    }
    return bot


async def reset_conversation(sid, reset=False):
    await get_bot(sid, cookie_path=get_cookie_file(sid, COOKIE_FILES, reset=reset)).reset()
    bots[sid]['expired'] = datetime.now() + timedelta(days=89, hours=23, minutes=55)  # 会话有效期为90天


def show_chatgpt(sid):
    for openid in conversation_ctr.get_openai_whitelist():
        if openid.decode() in sid:
            return 1
    return 0


def check_blocked(sid):
    for openid in conversation_ctr.get_blacklist():
        if openid.decode() in sid:
            return True


def make_response_data(status, text, suggests, message, num_in_conversation=-1, final=True):
    data = {
        'data': {
            'status': status,
            'text': text,
            'suggests': suggests,
            'message': message,
            'num_in_conversation': num_in_conversation,
        },
    }
    if final:
        logger.info(data)
    return data


async def generate_image(q, sid):
    resp = []
    if q and q.startswith('图片#') and q[3:].strip():
        images = await async_image_gen(q[3:].strip(), cookie_path=get_cookie_file(sid, COOKIE_FILES))
        resp = ['生成的图片如下：']
        for i, link in enumerate(images):
            resp.append(f'![image {i + 1}]({link})')
    return '\n'.join(resp)


async def ask_bing(ws, sid, q, style, reconnect=False):
    forbid_data = check_forbidden_words(sid, q)
    if forbid_data:
        await ws.send(raw_json.dumps({
            'final': True,
            'data': forbid_data,
        }))
        return
    last_not_final_text = ''
    resp = await generate_image(q, sid)
    if resp:
        await ws.send(raw_json.dumps({
            'final': True,
            'data': make_response_data('Success', resp, [], '')
        }))
        return
    index = 0
    async for response in get_bot(sid).ask_stream(
            q,
            conversation_style=ConversationStyle[style],
            reconnect=reconnect,
    ):
        final, res = response
        if final:
            processed_data = await process_data(res, q, sid, auto_reset=1)
            if processed_data['data']['status'] == 'Throttled':
                await reset_conversation(sid, reset=True)
                processed_data['data']['suggests'].append(q)
            if processed_data['data']['status'] == 'ProcessingMessage':
                #  await reset_conversation(sid)
                await asyncio.sleep(60)
                raise Exception(
                    'The last message is being processed. Please wait for a while before submitting further messages.'
                )
            if processed_data['data']['status'] == 'InternalError':
                if last_not_final_text:
                    processed_data = make_response_data(
                        'Success', last_not_final_text, [], '', processed_data['data']['num_in_conversation']
                    )
                else:
                    raise Exception(INTERNAL_ERROR)
            # 取消New Bing隐藏敏感内容
            if last_not_final_text and check_hidden(processed_data['data']['text']):
                processed_data = make_response_data(
                    'Success', last_not_final_text, [], '', processed_data['data']['num_in_conversation']
                )
            await ws.send(raw_json.dumps({
                'final': final,
                'data': processed_data
            }))
        else:
            if res and not check_hidden(res):
                last_not_final_text = res
                if index % 2 == 0:
                    await ws.send(raw_json.dumps({
                        'final': final,
                        'data': res
                    }))
                index += 1


def check_forbidden_words(sid, q):
    forbid_words = dfa.check_exist_word(q.strip())
    if forbid_words:
        data = make_response_data(
            'Success',
            FORBIDDEN_TIP,
            [],
            '',
            -1,
        )
        send_mail('forbid ' + sid, q + '\n包含敏感词：\n' + '\n'.join(forbid_words))
        return data


def check_limit(sid):
    incr = conversation_ctr.get_day_limit(sid)
    if show_chatgpt(sid):
        return False
    return True if incr > DAY_LIMIT else False


@app.websocket('/bing/chat')
async def ws_chat(_, ws):
    while True:
        msg, sid, q, style, try_times = '', '', '', '', 0
        reconnect = False
        try:
            data = await ws.recv()
            if not data:
                continue
            data = raw_json.loads(data)
            logger.info('[bing] Websocket receive data: %s', data)
            sid = data['sid']
            q = data['q']
            style = data.get('style', 'creative')
            if check_blocked(sid):
                raise Exception(NO_ACCESS)
            if check_limit(sid[-28:]):
                raise Exception(OVER_DAY_LIMIT)
            # 发生错误，重试10次
            try_times = 10
            reconnect = False
            await ask_bing(ws, sid, q, style, reconnect=reconnect)
        except KeyError:
            msg = SERVICE_NOT_AVALIABLE
        except Exception as e:
            logger.error('%s', traceback.format_exc())
            msg = str(e) or SERVICE_NOT_AVALIABLE
        if msg:
            if 'Cannot write to closing transport' in msg:
                reconnect = True
                # 等待上一个回答完成
                await asyncio.sleep(60)
            if 'Concurrent call to receive() is not allowed' in msg:
                await asyncio.sleep(60)
            if 'Connector is closed' in msg or 'The last message is being processed' in msg:
                reconnect = True
            if 'Your prompt has been blocked by Bing' in msg:
                try_times = 0
            if OVER_DAY_LIMIT in msg:
                try_times = 0
            while try_times and msg:
                try:
                    try_times -= 1
                    if NO_ACCESS in msg:
                        break
                    msg = ''
                    await ask_bing(
                        ws,
                        sid,
                        q,
                        style,
                        reconnect=reconnect,
                    )
                    reconnect = False
                except KeyError:
                    msg = SERVICE_NOT_AVALIABLE
                except Exception as e:
                    logger.error('%s', traceback.format_exc())
                    msg = str(e) or SERVICE_NOT_AVALIABLE
                if 'Cannot write to closing transport' in msg:
                    reconnect = True
                    # 等待上一个回答完成
                    await asyncio.sleep(60)
                if 'Concurrent call to receive() is not allowed' in msg:
                    await asyncio.sleep(60)
                if 'Connector is closed' in msg or 'The last message is being processed' in msg:
                    reconnect = True
                if 'Your prompt has been blocked by Bing' in msg:
                    try_times = 0
            if msg:
                reconnect = False
                await ws.send(raw_json.dumps({
                    'final': True,
                    'data': make_response_data('Error', msg, [q], msg)
                }))
                send_mail(sid, q + '\n' + msg)
                if NO_ACCESS in msg:
                    break
                msg = ''


async def do_chat(request):
    logger.info('[bing] Http request payload: %s', request.json)
    style = request.json.get('style', 'balanced')
    return await get_bot(request.json.get('sid')).ask(
        request.json.get('q'),
        conversation_style=ConversationStyle[style],
    )


async def process_data(res, q, sid, auto_reset=None):
    text = ''
    suggests = []
    status = res['item']['result']['value']
    if status == 'Success':
        item = res['item']['messages']
        try:
            user_message = item[0]
            offense = user_message['offense']
            if offense and offense == 'Offensive':
                send_mail('Offense!! ' + sid, str(res))
        except:
            pass
        if len(item) >= 2:
            index = 1
            # 多于2个adaptiveCards
            for i in range(2, len(item)):
                if 'adaptiveCards' in item[i]:
                    try:
                        text_ = item[i]['adaptiveCards'][0]['body'][0]['text']
                        if text_:
                            item[1]['adaptiveCards'][0]['body'][0]['text'] += ('\n' + text_)
                    except KeyError:
                        pass
                if 'suggestedResponses' in item[i]:
                    index = i
            if 'adaptiveCards' in item[1]:
                try:
                    text = item[1]['adaptiveCards'][0]['body'][0]['text']
                except KeyError:
                    pass
            if not text:
                if 'text' not in item[1]:
                    await reset_conversation(sid)
                    text = '抱歉，New Bing已结束当前聊天。现已开启新一轮对话。'
                    logger.error('响应异常：%s', res)
                else:
                    text = item[1]['text']
            text = re.sub(r'\[\^\d+\^\]', '', text)
            suggests = [x['text']
                        for x in item[index]['suggestedResponses']] if 'suggestedResponses' in item[index] else []
        else:
            await reset_conversation(sid)
            text = '抱歉，New Bing已结束当前聊天。现已开启新一轮对话。'
            logger.error('响应异常：%s', res)
            suggests = [q]
    msg = res['item']['result']['message'] if 'message' in res['item']['result'] else ''
    if auto_reset and ('New topic' in text or 'has expired' in msg):
        await reset_conversation(sid)
        status = 'Success'
        text = 'Thanks for this conversation! But I\'ve reached my limit. 现已开启新一轮对话。'
        if q not in suggests:
            suggests.append(q)
    return make_response_data(
        status, text, suggests, msg,
        res['item']['throttling']['numUserMessagesInConversation'] if 'throttling' in res['item'] else -1
    )


@app.post('/bing/chat')
async def chat(request):
    q = request.json.get('q', '')
    if check_blocked(request.json.get('sid')) or 'servicewechat.com/wxee7496be5b68b740' not in request.headers.get(
            'referer', ''):
        raise Exception(NO_ACCESS)
    sid = request.json.get('sid')
    if check_limit(sid[-28:]):
        raise Exception(OVER_DAY_LIMIT)
    forbid_data = check_forbidden_words(sid, q)
    if forbid_data:
        return json(forbid_data)
    resp = await generate_image(q, sid)
    if resp:
        return json(make_response_data('Success', resp, [], ''))
    res = await do_chat(request)
    auto_reset = request.json.get('auto_reset', '')
    data = await process_data(res, request.json.get('q'), sid, auto_reset)
    if data['data']['status'] == 'Throttled':
        await reset_conversation(sid, reset=True)
        res = await do_chat(request)
        data = await process_data(res, request.json.get('q'), sid, auto_reset)
    return json(data)


@app.route('/bing/reset')
async def reset(request):
    await reset_conversation(request.args.get('sid'))
    return json({'data': ''})


@app.route('/bing/openid')
async def openid(request):
    code = request.args.get('code')
    url = WX_URL % (APPID, APPSECRET, code)
    return json({'data': requests.get(url).json()})


# #########################################以下是openid接口##################################


def get_temperature(style):
    if style == ConversationStyle.balanced.name:
        return 0.6
    elif style == ConversationStyle.creative.name:
        return 1
    elif style == ConversationStyle.precise.name:
        return 0.2
    return 0.2


def get_history_conversation(sid):
    try:
        file = '/sanic/sessions/{}.openai'.format(sid)
        with open(file, 'rb') as f:
            OPENAI_CONVERSATION[sid] = pickle.load(f)
            logger.info('Reload %s openai session', sid)
            os.remove(file)
    except:
        pass
    return OPENAI_CONVERSATION[sid][-20:]


def num_tokens_from_messages(messages, model='gpt-3.5-turbo'):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding('cl100k_base')
    tokens_per_message = 0
    tokens_per_name = 0
    if model == 'gpt-3.5-turbo':
        return num_tokens_from_messages(messages, model='gpt-3.5-turbo-0301')
    elif model == 'gpt-4':
        return num_tokens_from_messages(messages, model='gpt-4-0314')
    elif model == 'gpt-3.5-turbo-0301':
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif model == 'gpt-4-0314':
        tokens_per_message = 3
        tokens_per_name = 1
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == 'name':
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


@app.websocket('/bing/ws_openai_chat')
async def ws_openai_chat(_, ws):
    while True:
        sid, q = '', ''
        try:
            data = await ws.recv()
            if not data:
                continue
            data = raw_json.loads(data)
            logger.info('[openai] Websocket receive data: %s', data)
            sid = data['sid']
            if not show_chatgpt(sid):
                raise Exception(NO_ACCESS)
            q = data['q']
            resp = await generate_image(q, sid)
            if resp:
                await ws.send(raw_json.dumps({
                    'final': True,
                    'data': make_response_data('Success', resp, [], '')
                }))
                continue
            style = data.get('style', 'creative')
            # 保存20个对话
            history_conversation = get_history_conversation(sid)
            history_conversation.insert(0, OPENAI_DEFAULT_PROMPT)
            history_conversation.append({
                'role': 'user',
                'content': q,
            })
            num_tokens = num_tokens_from_messages(history_conversation)
            if num_tokens > 4097:
                history_conversation = history_conversation[5:]
                history_conversation.insert(0, OPENAI_DEFAULT_PROMPT)
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo',
                messages=history_conversation,
                temperature=get_temperature(style),
                presence_penalty=1,
                stream=True,
            )
            chunks = []
            for chunk in response:
                chunk_message = chunk['choices'][0]['delta']
                if chunk_message:
                    if 'content' in chunk_message:
                        chunks.append(chunk_message['content'])
                        await ws.send(
                            raw_json.dumps({
                                'final': False,
                                'data': make_response_data('Success', ''.join(chunks), [], '', final=False)
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
            logger.error('%s', traceback.format_exc())
            send_mail(sid, q + '\n' + str(e))
            await ws.send(raw_json.dumps({
                'final': True,
                'data': make_response_data('Error', str(e), [], str(e))
            }))


@app.post('/bing/openai_chat')
async def openai_chat(request):
    sid, q = '', ''
    try:
        logger.info('[openai] Http request payload: %s', request.json)
        sid = request.json.get('sid')
        if not show_chatgpt(sid):
            raise Exception(NO_ACCESS)
        q = request.json.get('q')
        resp = await generate_image(q, sid)
        if resp:
            return json(make_response_data('Success', resp, [], ''))
        style = request.json.get('style', 'balanced')
        history_conversation = get_history_conversation(sid)
        history_conversation.insert(0, OPENAI_DEFAULT_PROMPT)
        history_conversation.append({
            'role': 'user',
            'content': q,
        })
        num_tokens = num_tokens_from_messages(history_conversation)
        if num_tokens > 4097:
            history_conversation = history_conversation[5:]
            history_conversation.insert(0, OPENAI_DEFAULT_PROMPT)
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo',
            messages=history_conversation,
            temperature=get_temperature(style),
            presence_penalty=1,
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
        logger.error('%s', traceback.print_exc())
        send_mail(sid, q + '\n' + str(e))
        return json(make_response_data('Error', str(e), [], str(e)))


@app.route('/bing/last_sync_time')
async def last_sync_time(request):
    return json({'last_sync_time': conversation_ctr.get_last_sync_time(request.args.get('sid'))})


@app.post('/bing/save')
async def save(request):
    if check_blocked(request.json.get('sid')) or 'servicewechat.com/wxee7496be5b68b740' not in request.headers.get(
            'referer', ''):
        raise Exception(NO_ACCESS)
    conversation_ctr.save(request.json.get('sid'), request.json.get('conversations'))
    return json({'saved': show_chatgpt(request.json.get('sid'))})


@app.route('/bing/query')
async def query(request):
    data = conversation_ctr.get_by_page(
        request.args.get('sid'), int(request.args.get('page', '1')), int(request.args.get('size', '10'))
    )
    return json({'data': data})


@app.post('/bing/delete')
async def delete(request):
    num = conversation_ctr.delete(request.json.get('sid'), request.json.get('conversation'))
    return json({'num': num})


@app.post('/bing/delete_all')
async def delete_all(request):
    conversation_ctr.delete_all(request.json.get('sid'))
    return json({})


@app.post('/bing/collect')
async def collect(request):
    conversation_ctr.operate_collect(
        request.json.get('sid'), request.json.get('conversation'), request.json.get('operate_type')
    )
    return json({})


@app.route('/bing/collect_query')
async def collect_query(request):
    data = conversation_ctr.get_collect_by_page(
        request.args.get('sid'), int(request.args.get('page', '1')), int(request.args.get('size', '10'))
    )
    return json({'data': data})


@app.post('/bing/share')
async def share(request):
    sid = request.json.get('sid')
    url = request.json.get('url')
    content = request.json.get('content')
    logger.info('[Memos] %s send %s to %s', sid, content, url)
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={'content': '#NewBing\n' + content}) as resp:
            if resp.status == 200:
                return json({'sent': 1})
    return json({'sent': 0})


@app.after_server_stop
def after_server_stop(*_):
    logger.info('Save sessions...')
    for sid, bot in bots.items():
        try:
            with open('/sanic/sessions/{}'.format(sid), 'wb') as f:
                pickle.dump(bot['bot'].chat_hub.request, f)
            logger.info('Save %s session success.', sid)
        except:
            logger.error('Save %s session error.', sid, exc_info=True)
    for sid, conversations in OPENAI_CONVERSATION.items():
        try:
            with open('/sanic/sessions/{}.openai'.format(sid), 'wb') as f:
                pickle.dump(conversations, f)
            logger.info('Save %s openai session success.', sid)
        except:
            logger.error('Save %s openai session error.', sid, exc_info=True)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
