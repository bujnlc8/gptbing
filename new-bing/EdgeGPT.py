from __future__ import annotations

import asyncio
import json
import os
import random
import ssl
import uuid
from enum import Enum
from typing import Generator, Literal, Optional, Union

import certifi
import httpx
import websockets.client as websockets

DELIMITER = "\x1e"

# Generate random IP between range 13.104.0.0/14
FORWARDED_IP = (f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}")

HEADERS = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9",
    "content-type": "application/json",
    "sec-ch-ua": '"Microsoft Edge";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
    "sec-ch-ua-arch": '"x86"',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version": '"111.0.1661.43"',
    "sec-ch-ua-full-version-list": '"Microsoft Edge";v="111.0.1661.43", "Not(A:Brand";v="8.0.0.0", "Chromium";v="111.0.5563.64"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": "",
    "sec-ch-ua-platform": '"macOS"',
    "sec-ch-ua-platform-version": '"11.7.3"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-ms-client-request-id": str(uuid.uuid4()),
    "x-ms-useragent": "azsdk-js-api-client-factory/1.0.0-beta.1 core-rest-pipeline/1.10.0 OS/MacIntel",
    "Referer": "https://www.bing.com/search?q=Bing+AI&showconv=1&FORM=hpcodx",
    "Referrer-Policy": "origin-when-cross-origin",
    "x-forwarded-for": FORWARDED_IP,
}

HEADERS_INIT = {
    "authority": "edgeservices.bing.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "sec-ch-ua": '"Microsoft Edge";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
    "sec-ch-ua-arch": '"x86"',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version": '"111.0.1661.43"',
    "sec-ch-ua-full-version-list": '"Microsoft Edge";v="111.0.1661.43", "Not(A:Brand";v="8.0.0.0", "Chromium";v="111.0.5563.64"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-model": '""',
    "sec-ch-ua-platform": '"macOS"',
    "sec-ch-ua-platform-version": '"11.7.3"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36 Edg/111.0.1661.43",
    "x-edge-shopping-flag": "1",
    "x-forwarded-for": FORWARDED_IP,
}

ssl_context = ssl.create_default_context()
ssl_context.load_verify_locations(certifi.where())


class NotAllowedToAccess(Exception):
    pass


class ConversationStyle(Enum):
    creative = [
        "nlu_direct_response_filter",
        "deepleo",
        "disable_emoji_spoken_text",
        "responsible_ai_policy_235",
        "enablemm",
        "h3imaginative",
        "clgalileo",
        "gencontentv3",
        "h3bsimagin",
        "serploc",
        "enbcdxpgpsr2",
        "healthansgnd",
        "rchlthalwlst",
        "dlreldeav2",
        "dv3sugg",
    ]
    balanced = [
        "nlu_direct_response_filter",
        "deepleo",
        "disable_emoji_spoken_text",
        "responsible_ai_policy_235",
        "enablemm",
        "galileo",
        "serploc",
        "enbcdxpgpsr2",
        "healthansgnd",
        "rchlthalwlst",
        "dlreldeav2",
        "dv3sugg",
    ]
    precise = [
        "nlu_direct_response_filter",
        "deepleo",
        "disable_emoji_spoken_text",
        "responsible_ai_policy_235",
        "enablemm",
        "h3precise",
        "serploc",
        "enbcdxpgpsr2",
        "healthansgnd",
        "rchlthalwlst",
        "dlreldeav2",
        "dv3sugg",
        "clgalileo",
        "h3bsprecise",
    ]


CONVERSATION_STYLE_TYPE = Optional[Union[ConversationStyle, Literal["creative", "balanced", "precise"]]]


def append_identifier(msg: dict) -> str:
    """
    Appends special character to end of message to identify end of message
    """
    # Convert dict to json string
    return json.dumps(msg) + DELIMITER


def get_rand_hex(length: int = 32) -> str:
    """
    Returns random hex string
    """
    return "".join(random.choice("0123456789abcdef") for _ in range(length))


class ChatHubRequest:
    """
    Request object for ChatHub
    """

    def __init__(
        self,
        conversation_signature: str,
        client_id: str,
        conversation_id: str,
        invocation_id: int = 0,
    ) -> None:
        self.struct: dict = {}

        self.client_id: str = client_id
        self.conversation_id: str = conversation_id
        self.conversation_signature: str = conversation_signature
        self.invocation_id: int = invocation_id

    def update(
        self,
        prompt: str,
        conversation_style: CONVERSATION_STYLE_TYPE,
        options: list | None = None,
    ) -> None:
        """
        Updates request object
        """
        if options is None:
            options = [
                "deepleo",
                "enable_debug_commands",
                "disable_emoji_spoken_text",
                "enablemm",
            ]
        if conversation_style:
            if not isinstance(conversation_style, ConversationStyle):
                conversation_style = getattr(ConversationStyle, conversation_style)
            options = conversation_style.value
        self.struct = {
            "arguments": [
                {
                    "source": "cib",
                    "optionsSets": options,
                    "allowedMessageTypes": [
                        "Chat",
                    ],
                    "sliceIds": [
                        "winmuid3tf",
                        "contctxp2tf",
                        "bcsrcf",
                        "ssoverlap50",
                        "sspltop5",
                        "sswebtop1",
                        "ttstmout",
                        "nopreloadsstf",
                        "rrsupp16",
                        "winlongmsg2tf",
                        "wpcssopt",
                        "creatgoglt2",
                        "creatorv2t",
                        "0415bficons0",
                        "418bs",
                        "420langdsats0",
                        "321sloc",
                        "407pgparser",
                        "0329resps0",
                        "418rchlth",
                        "asfixescf",
                        "udscahrfon",
                        "420deav2",
                    ],
                    "verbosity": "verbose",
                    "traceId": get_rand_hex(32),
                    "isStartOfSession": self.invocation_id == 0,
                    "message": {
                        "author": "user",
                        "inputMethod": "Keyboard",
                        "text": prompt,
                        "messageType": "Chat",
                    },
                    "conversationSignature": self.conversation_signature,
                    "participant": {
                        "id": self.client_id,
                    },
                    "conversationId": self.conversation_id,
                },
            ],
            "invocationId": str(self.invocation_id),
            "target": "chat",
            "type": 4,
        }
        self.invocation_id += 1


class Conversation:
    """
    Conversation API
    """

    def __init__(
        self,
        cookiePath: str = "",
        cookies: dict | None = None,
        proxy: str | None = None,
    ) -> None:
        self.struct: dict = {
            "conversationId": None,
            "clientId": None,
            "conversationSignature": None,
            "result": {
                "value": "Success",
                "message": None
            },
        }
        self.session = httpx.Client(
            proxies=proxy,
            timeout=120,
            headers=HEADERS_INIT,
        )
        if cookies is not None:
            cookie_file = cookies
        else:
            f = (
                open(cookiePath, encoding="utf8").read()
                if cookiePath else open(os.environ.get("COOKIE_FILE"), encoding="utf-8").read()
            )
            cookie_file = json.loads(f)
        for cookie in cookie_file:
            self.session.cookies.set(cookie["name"], cookie["value"])

        # Send GET request
        response = self.session.get(
            url=os.environ.get("BING_PROXY_URL") or "https://www.bing.com/turing/conversation/create"
        )
        if response.status_code != 200:
            response = self.session.get("https://edge.churchless.tech/edgesvc/turing/conversation/create")
            if response.status_code != 200:
                print(f"Status code: {response.status_code}")
                print(response.text)
                print(response.url)
                raise Exception("Authentication failed")
        try:
            self.struct = response.json()
            if self.struct["result"]["value"] == "UnauthorizedRequest":
                raise NotAllowedToAccess(self.struct["result"]["message"])
        except (json.decoder.JSONDecodeError, NotAllowedToAccess) as exc:
            raise Exception("Authentication failed. You have not been accepted into the beta.", ) from exc


class ChatHub:
    """
    Chat API
    """

    def __init__(self, conversation: Conversation) -> None:
        self.wss: websockets.WebSocketClientProtocol | None = None
        self.request: ChatHubRequest
        self.loop: bool
        self.task: asyncio.Task
        self.request = ChatHubRequest(
            conversation_signature=conversation.struct["conversationSignature"],
            client_id=conversation.struct["clientId"],
            conversation_id=conversation.struct["conversationId"],
        )

    async def ask_stream(
        self,
        prompt: str,
        wss_link: str,
        conversation_style: CONVERSATION_STYLE_TYPE = None,
    ) -> Generator[str, None, None]:
        """
        Ask a question to the bot
        """
        if self.wss:
            if not self.wss.closed:
                await self.wss.close()
        # Check if websocket is closed
        self.wss = await websockets.connect(
            wss_link,
            extra_headers=HEADERS,
            max_size=None,
            ssl=ssl_context,
            open_timeout=45,
        )
        await self.__initial_handshake()
        # Construct a ChatHub request
        self.request.update(prompt=prompt, conversation_style=conversation_style)
        # Send request
        await self.wss.send(append_identifier(self.request.struct))
        final = False
        while not final:
            objects = str(await self.wss.recv()).split(DELIMITER)
            for obj in objects:
                if obj is None or obj == "":
                    continue
                response = json.loads(obj)
                if response.get("type") == 1 and response["arguments"][0].get("messages", ):
                    resp_txt = response["arguments"][0]["messages"][0]["adaptiveCards"][0]["body"][0].get("text")
                    yield False, resp_txt
                elif response.get("type") == 2:
                    final = True
                    print(response)
                    yield True, response

    async def __initial_handshake(self):
        await self.wss.send(append_identifier({
            "protocol": "json",
            "version": 1
        }))
        await self.wss.recv()

    async def close(self):
        """
        Close the connection
        """
        if self.wss and not self.wss.closed:
            await self.wss.close()


class Chatbot:
    """
    Combines everything to make it seamless
    """

    def __init__(
        self,
        cookiePath: str = "",
        cookies: dict | None = None,
        proxy: str | None = None,
    ) -> None:
        self.cookiePath: str = cookiePath
        self.cookies: dict | None = cookies
        self.proxy: str | None = proxy
        self.chat_hub: ChatHub = ChatHub(Conversation(self.cookiePath, self.cookies, self.proxy))

    async def ask(
        self,
        prompt: str,
        wss_link: str = "wss://sydney.bing.com/sydney/ChatHub",
        conversation_style: CONVERSATION_STYLE_TYPE = None,
    ) -> dict:
        """
        Ask a question to the bot
        """
        async for final, response in self.chat_hub.ask_stream(
                prompt=prompt,
                conversation_style=conversation_style,
                wss_link=wss_link,
        ):
            if final:
                return response
        await self.chat_hub.wss.close()

    async def ask_stream(
        self,
        prompt: str,
        wss_link: str = "wss://sydney.bing.com/sydney/ChatHub",
        conversation_style: CONVERSATION_STYLE_TYPE = None,
    ) -> Generator[str, None, None]:
        """
        Ask a question to the bot
        """
        async for response in self.chat_hub.ask_stream(
                prompt=prompt,
                conversation_style=conversation_style,
                wss_link=wss_link,
        ):
            yield response

    async def close(self):
        """
        Close the connection
        """
        await self.chat_hub.close()

    async def reset(self):
        """
        Reset the conversation
        """
        await self.close()
        HEADERS["x-ms-client-request-id"] = str(uuid.uuid4())
        self.chat_hub = ChatHub(Conversation())
