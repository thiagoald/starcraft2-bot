from importlib import reload
import argparse

import sys
import asyncio

import sc2
import bot
from bot import SimpleBot
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer

import random

from sc2.constants import *
from sc2.position import Point2


class RampWallBot(sc2.BotAI):
    async def on_step(self, iteration):
        cc = self.units(COMMANDCENTER)
        if not cc.exists:
            return
        else:
            cc = cc.first

        if self.can_afford(SCV) and self.workers.amount < 16 and cc.noqueue:
            await self.do(cc.train(SCV))


        # Raise depos when enemies are nearby
        for depo in self.units(SUPPLYDEPOT).ready:
            for unit in self.known_enemy_units.not_structure:
                if unit.position.to2.distance_to(depo.position.to2) < 15:
                    break
            else:
                await self.do(depo(MORPH_SUPPLYDEPOT_LOWER))

        # Lower depos when no enemies are nearby
        for depo in self.units(SUPPLYDEPOTLOWERED).ready:
            for unit in self.known_enemy_units.not_structure:
                if unit.position.to2.distance_to(depo.position.to2) < 10:
                    await self.do(depo(MORPH_SUPPLYDEPOT_RAISE))
                    break

        depos = [
            Point2((max({p.x for p in d}), min({p.y for p in d})))
            for d in self.main_base_ramp.top_wall_depos
        ]

        depo_count = (self.units(SUPPLYDEPOT) | self.units(SUPPLYDEPOTLOWERED)).amount

        if self.can_afford(SUPPLYDEPOT) and not self.already_pending(SUPPLYDEPOT):
            if depo_count >= len(depos):
                return
            depo = list(depos)[depo_count]
            r = await self.build(SUPPLYDEPOT, near=depo, max_distance=2, placement_step=1)

class WorkerRushBot(sc2.BotAI):
    async def on_step(self, iteration):
        if iteration == 0:
            for worker in self.workers:
                await self.do(worker.attack(self.enemy_start_locations[0]))

def main():
    player_config = [
        Bot(Race.Terran, SimpleBot()),
        Computer(Race.Random, Difficulty.Easy)
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
