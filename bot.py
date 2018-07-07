import asyncio
from random import randint

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.player import Human
from pdb import set_trace


class Role:
    def __init__(self, agent, id_, state):
        self.agent = agent
        self.id = id_
        self.state = state


class CenterRole(Role):
    def __init__(self, agent, id_, state='building_first_scvs'):
        super().__init__(agent, id_, state)

    async def on_step(self, bot, iteration):
        print('Center {} is {}'.format(self.id, self.state))
        if self.state == 'building_first_scvs':
            if self.agent.is_idle and bot.can_afford(SCV) and bot.supply_left >= 1:
                await bot.do(self.agent.train(SCV))


class GatherRole(Role):
    def __init__(self, agent, id_, state='finding_closest_mineral'):
        super().__init__(agent, id_, state)

    def enemy_close(self, bot):
        for enemy_unit in bot.known_enemy_units:
            return self.agent.position.to2.distance_to(enemy_unit.position.to2) < 10

    async def on_step(self, bot, iteration):
        print('Gatherer {} is {}'.format(self.id, self.state))
        if self.state == 'slave':
            pass
        elif self.state == 'finding_closest_mineral':
            closest_mineral = bot.state.mineral_field.closest_to(self.agent)
            self.state = 'gathering'
            await bot.do(self.agent.gather(closest_mineral))
        elif self.state == 'gathering':
            if self.enemy_close(bot):
                place_idx = randint(0, len(bot.state.mineral_field))
                await bot.do(self.agent.move(bot.state.mineral_field[place_idx]))
                self.state = 'fleeing'
        elif self.state == 'fleeing':
            pass


class BuildRole(Role):
    def __init__(self, bot, agent, id_, state='slave'):
        super().__init__(agent, id_, state)

    def enemy_close(self, bot):
        for enemy_unit in bot.known_enemy_units:
            return self.agent.position.to2.distance_to(enemy_unit.position.to2) < 100

    def ready_to_build(self, build_ability):
        return self.agent.orders == [] or self.agent.orders[0].ability.id != build_ability

    async def find_place_to_build(self, bot, building_to_build, building_close):
        pos = None
        while pos is None:
            pos = await bot.find_placement(building_to_build,
                                           near=bot.units(building_close).closest_to(self.agent).position)
        return pos
    async def on_step(self, bot, iteration):
        print('Builder {} is {}'.format(self.id, self.state))
        if self.state == 'slave':
            pass
        elif self.state == 'building_supply_depot':
            if self.ready_to_build(AbilityId.TERRANBUILD_SUPPLYDEPOT) and bot.can_afford(SUPPLYDEPOT) and bot.supply_left < 10:
                if len(bot.units(SUPPLYDEPOT)) == 0:
                    pos = await self.find_place_to_build(bot, SUPPLYDEPOT, COMMANDCENTER)
                else:
                    pos = await self.find_place_to_build(bot, SUPPLYDEPOT, SUPPLYDEPOT)
                await bot.do(self.agent.build(SUPPLYDEPOT, pos))
                if pos is not None:
                    self.state = 'finishing_supply_depot'
        elif self.state == 'finishing_supply_depot':
            print('Build progress: {}', bot.units(SUPPLYDEPOT).closest_to(self.agent).build_progress)
            if bot.units(SUPPLYDEPOT).closest_to(self.agent).build_progress == 1.0:
                print('Finished!')
                self.state = 'building_supply_depot'
        elif self.state == 'building_barracks':
            if self.ready_to_build(AbilityId.TERRANBUILD_BARRACKS) and bot.can_afford(BARRACKS):
                if len(bot.units(BARRACKS)) == 0:
                    print('build supply depot')
                    pos = await bot.find_placement(BARRACKS, near=bot.units(COMMANDCENTER).closest_to(self.agent).position)
                    await bot.do(self.agent.build(BARRACKS, pos))
                else:
                    pos = await bot.find_placement(BARRACKS, near=bot.units(BARRACKS).closest_to(self.agent).position)
                    await bot.do(self.agent.build(BARRACKS, pos))
                if pos is not None:
                    self.state = 'finising_barracks'
        elif self.state == 'finishing_barracks':
            print('Build progress: {}', bot.units(BARRACKS).closest_to(self.agent).build_progress)
            if bot.units(BARRACKS).closest_to(self.agent).build_progress == 1.0:
                print('Finished!')
                self.state = 'building_barracks'


class ArmyGenRole(Role):
    def __init__(self, bot, agent, id_, state='generating_army'):
        super().__init__(agent, id_, state)

    async def on_step(self, bot, iteration):
        print('Army generator {} is {}'.format(self.id, self.state))
        if self.state == 'slave':
            pass
        elif self.state == 'generating_army':
            await bot.do(self.agent.train(MARINE))

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
    async def on_step(self, iteration):
        if iteration%200 == 0:
            print('Iteration {}'.format(iteration))
            # Initialize roles for units
            if iteration == 0:
                self.plan = 'first_scvs'
                self.id_ = 0
                self.gather_agents = []
                self.center_agents = []
                self.build_agents = []
                self.army_gen_agents = []
                self.roles_groups = [self.gather_agents,
                                    self.center_agents,
                                    self.build_agents,
                                    self.army_gen_agents]

                # SCVs are gatherers
                for id_, scv in enumerate(self.units(SCV)):
                    self.gather_agents.append(GatherRole(scv, self.id_ + id_))
                self.id_ += len(self.units(SCV))
                for id_, cc in enumerate(self.units(COMMANDCENTER)):
                    self.center_agents.append(CenterRole(cc, id_))
                self.id_ += len(self.units(COMMANDCENTER))

            print('Number of gatherers: {}'.format(len(self.gather_agents)))
            print('Number of center: {}'.format(len(self.center_agents)))
            print('Number of build: {}'.format(len(self.build_agents)))
            print('Number of army generators: {}'.format(len(self.army_gen_agents)))

            if self.plan == 'first_scvs':
                print('Creating first scvs')
                depot_builder = self.gather_agents.pop()
                depot_builder = depot_builder.agent
                barracks_builder = self.gather_agents.pop()
                barracks_builder = barracks_builder.agent
                self.build_agents.append(BuildRole(self, depot_builder, self.id_))
                self.build_agents.append(
                    BuildRole(self, barracks_builder, self.id_ + 1))
                self.id_ += 2
                self.build_agents[-1].state = 'building_supply_depot'
                self.build_agents[-2].state = 'building_barracks'
                self.plan = 'barracks'
            elif self.plan == 'barracks':
                print('Creating barracks')
                self.army_gen_agents = []
                for id_, barracks in enumerate(self.units(BARRACKS)):
                    self.army_gen_agents.append(
                        ArmyGenRole(self, barracks, self.id_ + id_))
                self.id_ += len(self.units(BARRACKS))

            loop = asyncio.get_event_loop()
            tasks = []
            self.roles_groups = [self.gather_agents,
                                self.center_agents,
                                self.build_agents,
                                self.army_gen_agents]
            for role_group in self.roles_groups:
                for agent in role_group:
                    tasks.append(loop.create_task(agent.on_step(self, iteration)))
            try:
                done, pending = await asyncio.wait(tasks, timeout=2.0)
                for task in pending:
                    task.cancel()
                print('End of iteration {}'.format(iteration))
            except:
                print('Skipping iteration...')


def main():
    sc2.run_game(sc2.maps.get("Abyssal Reef LE"), [
        Bot(Race.Terran, SimpleBot()),
        Computer(Race.Random, Difficulty.Hard)
    ], realtime=False, game_time_limit=(20 * 60))


if __name__ == '__main__':
    main()
