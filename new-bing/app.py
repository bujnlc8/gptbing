# coding=utf-8

import asyncio
import html
import json as raw_json
import os
import pickle
import re
import traceback
import urllib
from collections import defaultdict
from datetime import datetime, timedelta

import aiohttp
import openai
import requests
import tiktoken
from sanic import Sanic
from sanic.response import json

from Bard import Chatbot as BardBot
from BingImageCreator import async_image_gen
from common import DAY_LIMIT, FORBIDDEN_TIP, INTERNAL_ERROR, NO_ACCESS, OVER_DAY_LIMIT, \
    SERVICE_NOT_AVALIABLE
from conversation_ctr import conversation_ctr
from dfa import dfa
from EdgeGPT import Chatbot, ConversationStyle
from logger import logger
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
bard_bots = {}

# openai conversation
OPENAI_CONVERSATION = defaultdict(lambda: [])

OPENAI_DEFAULT_PROMPT = {
    'role': 'system',
    'content': "You are ChatGPT, a large language model trained by OpenAI. Follow the user's instructions carefully. Respond using markdown."  # noqa
}

HIDDEN_TEXTS = [
    '实在抱歉，我现在无法回答这个问题。',
    '嗯……对于这个问题很抱歉',
    'try a different topic.',
]


def wrap_q(q):
    if q.startswith('刚刚发生了点错误'):
        return q
    return '刚刚发生了点错误，请再次耐心地回答以下问题：' + q


def get_strip_words():
    res = []
    for prefix in ['你好，', '您好，']:
        for suffix in ['这里是Bing。', '这里是必应。', '这是Bing。', '这是必应。']:
            res.append('{}{}'.format(prefix, suffix))
    return res


STRIP_WORDS = get_strip_words()


def strip_hello(text):
    for x in STRIP_WORDS:
        text = text.replace(x, '')
    return text


def check_hidden(text):
    if not text:
        return False
    for x in HIDDEN_TEXTS:
        if x in text:
            return True
    return False


def get_cookie_file(sid, cookie_files, reset=False):
    # 优先获取最后一个
    if not reset and show_chatgpt(sid) & 1:
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
    # 1 chatgpt 2 bard
    for openid in conversation_ctr.get_openai_whitelist():
        if openid.decode() in sid:
            return 3
    return 2


def get_show_channel(sid, authority=0):
    res = [{
        'name': 'New Bing',
        'value': 'bing'
    }]
    if not authority:
        authority = show_chatgpt(sid)
    if authority & 1:
        res.append({
            'name': 'ChatGPT',
            'value': 'chatgpt'
        })
    if authority & 2:
        res.append({
            'name': 'Google Bard',
            'value': 'bard'
        })
    return res


def check_blocked(sid):
    for openid in conversation_ctr.get_blacklist():
        if openid.decode() in sid:
            return True


def make_response_data(status, text, suggests, message, num_in_conversation=-1, final=True):
    if not text.strip():
        text = '实在抱歉，我现在无法回答这个问题。 我还能为您提供哪些帮助？'
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


async def ask_bing(ws, sid, q, style, another_try=False):
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
    async for response in get_bot(sid).ask_stream(
            q,
            conversation_style=ConversationStyle[style],
            another_try=another_try,
    ):
        final, res = response
        if final:
            processed_data = await process_data(res, q, sid, auto_reset=1)
            if processed_data['data']['status'] == 'Throttled':
                await reset_conversation(sid, reset=True)
                processed_data['data']['suggests'].append(q)
            if processed_data['data']['status'] == 'ProcessingMessage':
                await asyncio.sleep(60)
                raise Exception(
                    'The last message is being processed. Please wait for a while before submitting further messages.'
                )
            if processed_data['data']['status'] == 'InternalError':
                if last_not_final_text and not last_not_final_text.startswith('正在搜索'):
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
            res = res.replace('Searching the web for', '正在搜索').replace('Generating answers for you', '正在为你生成答案')
            if res and not check_hidden(res):
                last_not_final_text = res
                await ws.send(raw_json.dumps({
                    'final': final,
                    'data': res,
                }))


def check_forbidden_words(sid, q):
    forbid_words = dfa.check_exist_word(q.strip())
    if forbid_words:
        data = make_response_data(
            'Success',
            FORBIDDEN_TIP + '\n敏感词如下：' + '、'.join(['**{}**'.format(x) for x in forbid_words]),
            [],
            '',
            -1,
        )
        send_mail('forbid ' + sid, q + '\n包含敏感词：\n' + '\n'.join(forbid_words))
        return data


def check_limit(sid):
    incr = conversation_ctr.get_day_limit(sid)
    if show_chatgpt(sid) & 1:
        return False
    return True if incr > DAY_LIMIT else False


@app.websocket('/bing/ws_common')
async def ws_common(_, ws):
    while True:
        msg, sid, q, style, try_times = '', '', '', '', 0
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
            await ask_bing(ws, sid, q, style)
            msg = ''
        except KeyError:
            msg = SERVICE_NOT_AVALIABLE
        except Exception as e:
            logger.error('%s', traceback.format_exc())
            msg = str(e) or SERVICE_NOT_AVALIABLE
        if msg:
            while try_times and msg and 'sanic.exceptions' not in msg:
                try:
                    try_times -= 1
                    if OVER_DAY_LIMIT in msg or NO_ACCESS in msg or 'Your prompt has been blocked by Bing' in msg:
                        break
                    if 'Concurrent call to receive() is not allowed' in msg:
                        await asyncio.sleep(45)
                    another_try = False
                    if 'Cannot write to closing transport' in msg:
                        another_try = True
                    if 'Unexpected message type' in msg:
                        another_try = True
                    await ask_bing(
                        ws,
                        sid,
                        wrap_q(q) if '现已开启新一轮对话' not in msg else q,
                        style,
                        another_try=another_try,
                    )
                    msg = ''
                except KeyError:
                    msg = SERVICE_NOT_AVALIABLE
                except Exception as e:
                    logger.error('%s', traceback.format_exc())
                    msg = str(e) or SERVICE_NOT_AVALIABLE
            if msg:
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


async def process_data(res, q, sid, auto_reset=None, auto_new_talk=True):
    text = ''
    suggests = []
    status = res['item']['result']['value']
    offensive = False
    if status == 'Success':
        item = res['item']['messages']
        try:
            user_message = item[0]
            offense = user_message['offense']
            if offense and offense == 'Offensive':
                offensive = True
                send_mail('Offense!! ' + sid, str(res))
        except:
            pass
        if len(item) >= 2:
            index = -1
            for i in range(1, len(item)):
                if 'adaptiveCards' in item[i]:
                    try:
                        text += item[i]['adaptiveCards'][0]['body'][0]['text'] + '\n'
                    except KeyError:
                        pass
                if 'suggestedResponses' in item[i]:
                    index = i
            if not text:
                if 'text' not in item[-1]:
                    await reset_conversation(sid)
                    text = '抱歉，New Bing已结束当前聊天。现已开启新一轮对话。'
                    logger.error('响应异常：%s', res)
                else:
                    text = item[-1]['text']
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
        if auto_new_talk:
            raise Exception('Thanks for this conversation! But I\'ve reached my limit. 现已开启新一轮对话。')
        status = 'Success'
        text = 'Thanks for this conversation! But I\'ve reached my limit. 现已开启新一轮对话。'
        if q not in suggests:
            suggests.append(q)
    if offensive:
        text += '\n**温馨提醒：你已触发New Bing的Offensive检测机制，请文明提问哦😊，次数过多将被禁止使用！**'
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
    data = await process_data(res, request.json.get('q'), sid, auto_reset, auto_new_talk=False)
    if data['data']['status'] == 'Throttled':
        await reset_conversation(sid, reset=True)
        res = await do_chat(request)
        data = await process_data(res, request.json.get('q'), sid, auto_reset, auto_new_talk=False)
    return json(data)


@app.route('/bing/reset')
async def reset(request):
    sid = request.args.get('sid')
    if not sid:
        raise Exception('参数错误')
    if not check_blocked(sid):
        await reset_conversation(sid)
    return json({'data': ''})


@app.route('/bing/openid')
async def openid(request):
    code = request.args.get('code')
    url = WX_URL % (APPID, APPSECRET, code)
    data = requests.get(url).json()
    authority = show_chatgpt(data['openid'])
    data['saved'] = authority
    data['channel'] = get_show_channel(data['openid'], authority=authority)
    return json({'data': data})


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
            if not (show_chatgpt(sid) & 1):
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
            if num_tokens > 4096:
                history_conversation = history_conversation[5:]
                history_conversation.insert(0, OPENAI_DEFAULT_PROMPT)
            response = openai.ChatCompletion.create(
                model='gpt-3.5-turbo-0613',
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
        if not (show_chatgpt(sid) & 1):
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
        if num_tokens > 4096:
            history_conversation = history_conversation[5:]
            history_conversation.insert(0, OPENAI_DEFAULT_PROMPT)
        response = openai.ChatCompletion.create(
            model='gpt-3.5-turbo-0613',
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
    sid = request.json.get('sid')
    if check_blocked(sid) or 'servicewechat.com/wxee7496be5b68b740' not in request.headers.get('referer', ''):
        raise Exception(NO_ACCESS)
    conversation_ctr.save(sid, request.json.get('conversations'))
    authority = show_chatgpt(sid)
    return json({
        'saved': authority,
        'channel': get_show_channel(sid, authority=authority),
    })


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


# #########################################以下是Bard接口##################################


async def get_bard_bot(sid) -> BardBot:
    if sid in bard_bots:
        return bard_bots[sid]
    bot = await BardBot.create(file_path='/sanic/sessions/{}.bard'.format(sid))
    bard_bots[sid] = bot
    return bot


@app.websocket('/bing/ws_bard')
async def ws_bard(_, ws):
    while True:
        msg, sid, q = '', '', ''
        try:
            data = await ws.recv()
            if not data:
                continue
            data = raw_json.loads(data)
            logger.info('[bard] Websocket receive data: %s', data)
            sid = data['sid']
            if not (show_chatgpt(sid) & 2):
                raise Exception(NO_ACCESS)
            if check_blocked(sid):
                raise Exception(NO_ACCESS)
            q = data['q']
            bot = await get_bard_bot(sid)
            resp = await bot.ask(q)
            text = resp['content'].replace('\r\n', '\n')
            if resp.get('images'):
                text += '\n'
                for x in resp['images']:
                    if x.startswith('http'):
                        text += '![]({})'.format(x) + '\n'
                    else:
                        text += x + '\n'
            await ws.send(raw_json.dumps({
                'final': True,
                'data': make_response_data('Success', text, [], msg)
            }))
        except Exception as e:
            logger.error('%s', traceback.format_exc())
            msg = str(e) or SERVICE_NOT_AVALIABLE
            await ws.send(raw_json.dumps({
                'final': True,
                'data': make_response_data('Error', msg, [q], msg)
            }))


def process_content(content):
    matches = re.findall(r'(\[\d+\]):\s(http[^"]*)\s', content)
    content = re.sub(r'\[\d+\]:\shttp.*', '', content)
    content = content.strip()
    for k, v in matches:
        content = content.replace(k, '{}({})'.format(k, v))
    content = content.replace(' ```', '```').replace(' ```', '```')
    return strip_hello(content)


def put_refresh(url, token):
    if conversation_ctr.redis_client.get('bing:wiz:token:{}'.format(token)):
        return
    pareses = urllib.parse.urlparse(url)
    host = pareses.netloc
    if host == 'ks.wiz.cn':
        host = 'as.wiz.cn'
    refresh_url = '{}://{}/as/user/keep'.format(pareses.scheme, host)
    # remember refresh_url
    conversation_ctr.redis_client.set('bing:wiz:refresh_url:{}'.format(token), refresh_url)
    conversation_ctr.redis_client.set('bing:wiz:token:{}'.format(token), 1, 10)
    logger.info('[WizToken] %s 加入刷新队列, refresh_url: %s.', token, refresh_url)


@app.post('/bing/share')
async def share(request):
    sid = request.json.get('sid')
    url = request.json.get('url')
    content = request.json.get('content')
    title = request.json.get('title', '')
    # 0 memos 1 flomo 2 wiznote
    app_type = request.json.get('app_type', 0)
    logger.info('[Memos] %s send to %s', sid, url)
    async with aiohttp.ClientSession() as session:
        if app_type == 2:
            # url = 'https://$host/ks/note/create/$kbGuid/$token'
            url_split = url.split('/')
            kb_guid = url_split[-2]
            token = url_split[-1]
            data = {
                'html': html.escape(process_content(content)).replace('\n', '<br/>'),
                'title': title,
                'category': '/My Notes/',
                'kbGuid': kb_guid,
            }
            headers = {
                'X-Wiz-Token': token,
                'User-Agent': 'NewBBot'
            }
            url = '/'.join(url_split[:-1])
            async with session.post(url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    resp = await resp.json()
                    if resp['returnCode'] == 200:
                        # 将token加入刷新，可能是自部署服务，需要带上host
                        put_refresh(url, token)
                        return json({'sent': 1})
                    else:
                        logger.info('[WizNote] url: %s, data: %s, resp: %s', url, data, resp)
        else:
            async with session.post(url, json={'content': process_content(content) + '\n#NewBing'}) as resp:
                if resp.status == 200:
                    if app_type == 0:
                        return json({'sent': 1})
                    resp = await resp.json()
                    if resp['code'] == 0:
                        return json({'sent': 1})
    return json({'sent': 0})


@app.after_server_stop
async def after_server_stop(*_):
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
            logger.info('Save %s Openai session success.', sid)
        except:
            logger.error('Save %s Openai session error.', sid, exc_info=True)
    for sid, bot in bard_bots.items():
        try:
            await bot.save_conversation()
            logger.info('Save %s Bard session success.', sid)
        except:
            logger.error('Save %s Bard session error.', sid, exc_info=True)


if __name__ == '__main__':
    if os.environ.get('REFRESH_WIZ'):
        while True:
            try:
                conversation_ctr.refresh_wiz_token()
            except:
                logger.error('refresh_wiz_token error occor', exc_info=True)
    else:
        app.run(host='0.0.0.0', port=8000)
