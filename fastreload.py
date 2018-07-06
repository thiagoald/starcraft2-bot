from importlib import reload
import argparse

import sys
import asyncio

import sc2
import bot
from bot import SimpleBot
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer

def main():
    player_config = [
        Bot(Race.Terran, SimpleBot()),
        Computer(Race.Terran, Difficulty.Medium)
    ]

    gen = sc2.main._host_game_iter(
        sc2.maps.get("Abyssal Reef LE"),
        player_config,
        realtime=False
    )

    while True:
        r = next(gen)

        input("Press enter to reload ")

        reload(bot)
        player_config[0].ai = bot.SimpleBot()
        gen.send(player_config)

if __name__ == "__main__":
    main()
