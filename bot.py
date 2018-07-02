import asyncio
from random import randint

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.player import Human
from pdb import set_trace


class Role:
    async def on_step(self, bot, iteration):
        raise NotImplementedError


class GatheringRole(Role):
    def __init__(self, agent, id_):
        self.agent = agent
        self.id = id_
        self.state = 'nothing'

    def enemy_close(self, bot):
        print('len(bot.known_enemy_units) = ', len(bot.known_enemy_units))
        print('bot.known_enemy_units = ', bot.known_enemy_units)
        for enemy_unit in bot.known_enemy_units:
            return self.agent.position.to2.distance_to(enemy_unit.position.to2) < 100

    async def on_step(self, bot, iteration):
        if self.state == 'nothing':
            closest_mineral = bot.state.mineral_field.closest_to(self.agent)
            self.state = 'gathering'
            await bot.do(self.agent.gather(closest_mineral))
        elif self.state == 'gathering':
            if self.enemy_close(bot):
                set_trace()
                place_idx = randint(1, len(bot.enemy_start_locations))
                await bot.do(self.agent.move(bot.enemy_start_locations[place_idx]))

# class BuildingRole(Role):
#     def __init__(self, agent, id_):


# class MilitarRole(Role):
#     def heavy_computation(self):
#         i = 0
#         # while i < 1e8:
#         #     i += 1

#     async def on_step(self, bot, iteration):
#         loop = asyncio.get_event_loop()
#         await loop.run_in_executor(None, self.heavy_computation)
#         await bot.chat_send("MilitarAgent on iteration: " + str(iteration))

# class Coordinator(Role):
#     async def on_step(self, bot, iteration):
#         await bot.do()

class SimpleBot(sc2.BotAI):
    def start(self):
        self.gathering_agents = []
        self.roles_groups = [self.gathering_agents]
        for id_, scv in enumerate(self.units(SCV)):
            self.gathering_agents.append(GatheringRole(scv, id_))

    async def on_step(self, iteration):

        if iteration == 0:
            self.start()

        loop = asyncio.get_event_loop()
        tasks = []
        for role_group in self.roles_groups:
            for agent in role_group:
                tasks.append(loop.create_task(agent.on_step(self, iteration)))
        try:
            done, pending = await asyncio.wait(tasks, timeout=2.0)
            for task in pending:
                task.cancel()
        except:
            print('Skipping iteration...')


def main():
    sc2.run_game(sc2.maps.get("Abyssal Reef LE"), [
        Bot(Race.Terran, SimpleBot()),
        Computer(Race.Random, Difficulty.Hard)
    ], realtime=False, game_time_limit=(20*60))


if __name__ == '__main__':
    main()