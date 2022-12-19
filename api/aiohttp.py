#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import asyncio
import aiohttp


async def send(session, url, method, response_type):
    async with session.request(method, url) as resp:
        print(resp.status)
        return await getattr(resp, response_type)()


async def main(base_url, url, method, response_type):
    async with aiohttp.ClientSession(base_url) as session:
        resp = await send(session, url, method, response_type)
        return resp


# asyncio.run(
#     main(
#         base_url='http://httpbin.org',
#         url='/get',
#         method='get',
#         response_type="json"
#     )
# )


async def communicate(session, url, method, response_type):
    async with session.request(method, url) as resp:
        print(resp.status)
        return await getattr(resp, response_type)()


class Communicate:
    def __init__(self, base_url, **kwargs):
        self.base_url = base_url
        self.kwargs = kwargs

    async def send(self, method, url, response_type, **kwargs):
        async with aiohttp.ClientSession(self.base_url, **self.kwargs) as session:
            resp = await communicate(session, url, method, response_type, **kwargs)
            return resp


# client = Communicate("http://httpbin.org")
# asyncio.run(client.send(method='get', url='/get', response_type="json"))
