import os
import json
import re
from typing import Iterable
from enum import Enum
from datetime import datetime, time, timezone, timedelta
import asyncio
import threading
import random

import discord
from discord.embeds import Embed


offset = timezone(timedelta(hours=3))

class Actions(Enum):
    NOTHING = 0
    DOWNGRADE = 1
    PROMOTION = 2

class MyClient(discord.Client):
    timer: threading.Timer = None

    async def on_ready(self):
        self._start_timer()

    def _start_timer(self):
        settings = ''.join(open('settings.json', 'r').readlines())
        settings = json.loads(settings)

        seconds = self._get_seconds_to_changetime(settings.pop('changetimes'))
        print(seconds)
        
        if self.timer:
            self.timer.cancel()
        
        self.timer = threading.Timer(seconds, self.change_shareholders, settings.values())
        self.timer.start()
    
    def _get_seconds_to_changetime(self, times: Iterable[Iterable[int]]) -> int:
        now = datetime.now(offset)
        print(now)
        times = tuple(time(*parameters) for parameters in times)
        time_ = self._get_nearest_time(now, times)
        print(time_)

        changetime = datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=time_.hour,
                minute=time_.minute,
                second=time_.second,
                microsecond=time_.microsecond,
                tzinfo=offset
        )

        if now.time() > time_:
            changetime += timedelta(days=1)

        return (changetime-now).seconds

    def _get_nearest_time(self, now: datetime, times: Iterable[time]) -> time:
        now = now+timedelta(minutes=1)
        if now.time() > max(times):
            return min(times)
        else:
            for time in times:
                if now.time() < time:
                    return time
        raise ValueError('times must not be empty')
        
    def change_shareholders(self, server_id: int, channel_id: int):
        guild = self.get_guild(server_id)
        channel = guild.get_channel(channel_id)

        self.loop.create_task(self._change_shareholders(channel))
        
        self._start_timer()

    async def _change_shareholders(self, channel: discord.TextChannel):
        shareholders = await self._get_shareholders(channel)

        total_messages = []
        for shareholder in shareholders:
            info = (await self.get(channel, f'*item-info {shareholder}')).embeds[0]
            price = await self._get_price_shareholder(info)

            choice = random.choice(list(Actions))
            if choice is Actions.NOTHING:
                total_messages.append(f'{shareholder} по прежнему {price}')
            else:
                if choice is Actions.DOWNGRADE:
                    procent = 1 - random.randint(1, 50) * 0.01
                    action = 'понизились'
                else:
                    procent = 1 + random.randint(1, 100) * 0.01
                    action = 'повысились'

                price = int(price * procent)
                await channel.send(f'*edit-item price "{shareholder}" {price}')
                total_messages.append(f'{shareholder} {action} до {price}')
                await asyncio.sleep(1)
        
        await channel.send('ИТОГО: '+', '.join(total_messages))

    shareholders_regex = re.compile(r'\d - (Акции .+)')
    async def _get_shareholders(self, channel: discord.TextChannel) -> list[str]:
        cls = self.__class__
        message = await self.get(channel, '*item-info Акции')

        shareholders = message.embeds[0].description

        return [shareholder.group(1) for shareholder in 
                cls.shareholders_regex.finditer(shareholders)]

    coin_regex = re.compile(r'<.+>')
    async def _get_price_shareholder(self, info: Embed) -> int:
        cls = self.__class__
        print(info)

        for field in info.fields:
            if field.name == 'Price':
                price = cls.coin_regex.sub('', field.value) 
                price = price.replace(',', '')
                return int(price)
        raise ValueError('Embed fields is empty')

    async def get(self, channel: discord.TextChannel, content: str) -> discord.Message:
        await channel.send(content)
        while not channel.last_message.embeds:
            await asyncio.sleep(1)
        return channel.last_message


CLIENT_TOKEN = os.getenv("BOT_TOKEN")
client = MyClient()
client.run(CLIENT_TOKEN)
