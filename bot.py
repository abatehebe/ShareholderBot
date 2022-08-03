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

        seconds = self._get_seconds_to_changetime(settings.pop('changehours'))
        print(seconds)
        
        if self.timer:
            self.timer.cancel()
        
        self.timer = threading.Timer(seconds, self.change_shareholders, settings.values())
        self.timer.start()
    
    def _get_seconds_to_changetime(self, hours: Iterable[int]) -> int:
        now = datetime.now(offset)
        hour = self._get_nearest_hour(now, hours)
        print(hour)

        changetime = datetime(
                year=now.year,
                month=now.month,
                day=now.day,
                hour=hour,
                tzinfo=offset
        )

        if now.time() > time(hour=hour):
            changetime += timedelta(days=1)

        return (changetime-now).seconds

    def _get_nearest_hour(self, now: datetime, hours: Iterable[int]) -> int:
        if now.time() > time(hour=max(hours)):
            return min(hours)
        else:
            for hour in hours:
                if now.time() < time(hour=hour):
                    print(now.time())
                    return hour
        
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

    async def _get_shareholders(self, channel: discord.TextChannel) -> list[str]:
        message = await self.get(channel, '*item-info Акции')

        shareholders = message.embeds[0].description
        shareholders_regex = re.compile(r'\d - (Акции .+)')

        return [shareholder.group(1) for shareholder in 
                shareholders_regex.finditer(shareholders)]

    async def _get_price_shareholder(self, info: Embed) -> int:
        for field in info.fields:
            if field.name == 'Price':
                price = field.value.replace('<:fenix_money:867086679810506792>', '')
                return int(price)

    async def get(self, channel: discord.TextChannel, content: str) -> discord.Message:
        await channel.send(content)
        await asyncio.sleep(10)
        return channel.last_message


CLIENT_TOKEN = os.getenv("BOT_TOKEN")
client = MyClient()
client.run(CLIENT_TOKEN)
