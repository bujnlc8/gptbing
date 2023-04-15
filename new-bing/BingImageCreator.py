import asyncio
import json
import os

import aiohttp
import regex
import requests

BING_URL = "https://www.bing.com"

HEADERS = {
    'authority': 'www.bing.com',
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,mt;q=0.5',
    'cache-control': 'max-age=0',
    'origin': 'https://www.bing.com',
    'referer': 'https://www.bing.com/images/create?FORM=GENILP',
    'sec-ch-ua': '"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
    'sec-ch-ua-arch': '"x86"',
    'sec-ch-ua-bitness': '"64"',
    'sec-ch-ua-full-version': '"112.0.1722.48"',
    'sec-ch-ua-full-version-list': '"Chromium";v="112.0.5615.121", "Microsoft Edge";v="112.0.1722.48", "Not:A-Brand";v="99.0.0.0"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-model': '""',
    'sec-ch-ua-platform': '"macOS"',
    'sec-ch-ua-platform-version': '"11.7.6"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'sec-ms-gec': 'BA74B980CD7362F853CAF5B6FB737DD3157933A56C2D47A6BA47EDEECCCA42FA',
    'sec-ms-gec-version': '1-112.0.1722.48',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.48',
    'x-forwarded-for': '1.1.1.1',
}


class ImageGenAsync:
    """
    Image generation by Microsoft Bing
    Parameters:
        auth_cookie: str
    """

    def __init__(self, auth_cookie: str, quiet: bool = True) -> None:
        self.session = aiohttp.ClientSession(
            headers=HEADERS,
            cookies={"_U": auth_cookie},
            trust_env=True,
        )
        self.quiet = quiet

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
        if not self.quiet:
            print("Sending request...")
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
                        print(f"ERROR: {response3.text}")
                        raise Exception("Redirect failed")
                    response = response3
        # Get redirect URL
        redirect_url = response.headers["Location"].replace("&nfy=1", "")
        request_id = redirect_url.split("id=")[-1]
        await self.session.get(f"{BING_URL}{redirect_url}")
        # https://www.bing.com/images/create/async/results/{ID}?q={PROMPT}
        polling_url = f"{BING_URL}/images/create/async/results/{request_id}?q={url_encoded_prompt}"
        # Poll for results
        if not self.quiet:
            print("Waiting for results...")
        while True:
            if not self.quiet:
                print(".", end="", flush=True)
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
