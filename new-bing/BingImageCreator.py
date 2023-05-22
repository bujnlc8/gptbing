import asyncio
import json
import os

import random

import aiohttp
import regex
import requests
from logger import logger

BING_URL = os.environ.get("BING_URL", "https://www.bing.com")

FORWARDED_IP = (f"13.{random.randint(104, 107)}.{random.randint(0, 255)}.{random.randint(0, 255)}")

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "referrer": "https://www.bing.com/images/create/",
    "origin": "https://www.bing.com",
    "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63",
    "x-forwarded-for": FORWARDED_IP,
}


class ImageGenAsync:
    """
    Image generation by Microsoft Bing
    Parameters:
        auth_cookie: str
    """

    def __init__(self, auth_cookie: str) -> None:
        self.session = aiohttp.ClientSession(
            headers=HEADERS,
            cookies={"_U": auth_cookie},
            trust_env=True,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *excinfo) -> None:
        await self.session.close()

    async def get_images(self, prompt: str) -> list:
        """
        Fetches image links from Bing
        Parameters:
            prompt: str
        """
        url_encoded_prompt = requests.utils.quote(prompt)
        # https://www.bing.com/images/create?q=<PROMPT>&rt=3&FORM=GENCRE
        url = f"{BING_URL}/images/create?q={url_encoded_prompt}&rt=4&FORM=GENCRE"
        async with self.session.post(url, allow_redirects=False) as response:
            content = await response.text()
            if "this prompt has been blocked" in content.lower():
                raise Exception("Your prompt has been blocked by Bing. Try to change any bad words and try again.", )
            if response.status != 302:
                # if rt4 fails, try rt3
                url = (f"{BING_URL}/images/create?q={url_encoded_prompt}&rt=3&FORM=GENCRE")
                async with self.session.post(
                        url,
                        allow_redirects=False,
                        timeout=200,
                ) as response3:
                    if response3.status != 302:
                        logger.error('url: %s, status: %s, response: %s', url, response3.status, response3.text)
                        raise Exception("画图服务不可用，请稍后再试！")
                    response = response3
        # Get redirect URL
        redirect_url = response.headers["Location"].replace("&nfy=1", "")
        request_id = redirect_url.split("id=")[-1]
        await self.session.get(f"{BING_URL}{redirect_url}")
        # https://www.bing.com/images/create/async/results/{ID}?q={PROMPT}
        polling_url = f"{BING_URL}/images/create/async/results/{request_id}?q={url_encoded_prompt}"
        while True:
            # By default, timeout is 300s, change as needed
            response = await self.session.get(polling_url)
            if response.status != 200:
                raise Exception("Could not get results")
            content = await response.text()
            if content and content.find("errorMessage") == -1:
                break

            await asyncio.sleep(1)
            continue
        # Use regex to search for src=""
        image_links = regex.findall(r'src="([^"]+)"', content)
        # Remove size limit
        normal_image_links = [link.split("?w=")[0] for link in image_links]
        # Remove duplicates
        normal_image_links = list(set(normal_image_links))

        # Bad images
        bad_images = [
            "https://r.bing.com/rp/in-2zU3AJUdkgFe7ZKv19yPBHVs.png",
            "https://r.bing.com/rp/TX9QuO3WzcCJz1uaaSwQAz39Kb0.jpg",
        ]
        for im in normal_image_links:
            for x in bad_images:
                if im in x:
                    raise Exception("Bad images")
        # No images
        if not normal_image_links:
            raise Exception("No images")
        return normal_image_links


async def async_image_gen(prompt, cookie=""):
    if not cookie:
        f = open(os.environ.get("COOKIE_FILE"), encoding="utf-8").read()
        cookie_file = json.loads(f)
        for x in cookie_file:
            if x["name"] == "_U":
                cookie = x["value"]
                break
    async with ImageGenAsync(cookie) as image_generator:
        return await image_generator.get_images(prompt)
