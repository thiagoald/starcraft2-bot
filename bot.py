import asyncio
from random import randint

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.player import Human
from sc2.position import Point2
from pdb import set_trace
from time import time


def close_enemies(bot,
                  agent,
                  distance):
    close_enemies = []
    for enemy in bot.known_enemy_units:
        if agent.position.to2.distance_to(enemy.position.to2) < distance:
            close_enemies.append(enemy)
    return close_enemies


async def find_place_to_build(bot,
                              agent,
                              building_to_build,
                              max_distance=20,
                              buildings_close=None,
                              position_close=None,
                              placement_step=2):
    pos = None
    print(buildings_close, position_close)
    while pos is None:
        if buildings_close is not None:
            pos_near = []
            for building in buildings_close:
                pos_near.append(bot.units(building).closest_to(agent).position)
            print(pos_near)
            set_trace()
            pos_near = pos_near[0]
        elif position_close is not None:
            pos_near = position_close
        pos = await bot.find_placement(building_to_build,
                                       max_distance=max_distance,
                                       near=pos_near,
                                       placement_step=placement_step)
    return pos


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
            if self.agent.is_idle and bot.can_afford(SCV) and bot.supply_left >= 1 and len(bot.units(SCV)) < 16:
                await bot.do(self.agent.train(SCV))


class GatherRole(Role):
    def __init__(self, agent, id_, state='finding_closest_mineral'):
        super().__init__(agent, id_, state)

    async def on_step(self, bot, iteration):
        print('Gatherer {} is {}'.format(self.id, self.state))
        if self.state == 'slave':
            pass
        elif self.state == 'finding_closest_mineral':
            closest_mineral = bot.state.mineral_field.closest_to(self.agent)
            self.state = 'gathering'
            await bot.do(self.agent.gather(closest_mineral))
        elif self.state == 'gathering':
            pass
            # if close_enemies(bot, self.agent, 20) != []:
            #     place_idx = randint(0, len(bot.state.mineral_field))
            #     await bot.do(self.agent.move(bot.state.mineral_field[place_idx]))
            #     self.state = 'fleeing'
        elif self.state == 'fleeing':
            if self.agent.is_idle and bot.can_afford(COMMANDCENTER):
                pos = await find_place_to_build(
                    bot, self.agent, COMMANDCENTER, position_close=self.agent.position, max_distance=10)
                await bot.do(self.agent.build(COMMANDCENTER))
            pass


class BuildRole(Role):
    def __init__(self, bot, agent, id_, state='slave'):
        super().__init__(agent, id_, state)

    def ready_to_build(self, build_ability):
        return self.agent.orders == [] or self.agent.orders[0].ability.id != build_ability

    async def build_ramp_depots(self, bot):
        depos = [
            Point2((max({p.x for p in d}), min({p.y for p in d})))
            for d in bot.main_base_ramp.top_wall_depos
        ]

        depo_count = (bot.units(SUPPLYDEPOT) |
                      bot.units(SUPPLYDEPOTLOWERED)).amount

        if bot.can_afford(SUPPLYDEPOT) and not bot.already_pending(SUPPLYDEPOT):
            if depo_count >= len(depos):
                return
            depo = list(depos)[depo_count]
            pos = await find_place_to_build(bot,
                                            self.agent,
                                            SUPPLYDEPOT,
                                            max_distance=2,
                                            position_close=depo,
                                            placement_step=1)
            await bot.do(self.agent.build(SUPPLYDEPOT, pos))

    async def on_step(self, bot, iteration):
        print('Builder {} is {}'.format(self.id, self.state))
        if self.state == 'slave':
            pass
        elif self.state == 'building_supply_depot':
            print('Minerals')
            print(bot.minerals)
            if self.ready_to_build(AbilityId.TERRANBUILD_SUPPLYDEPOT) and bot.can_afford(SUPPLYDEPOT) and bot.supply_left < 10:
                print('len(bot.units(SUPPLYDEPOT)) + len(bot.units(SUPPLYDEPOTLOWERED))')
                print(len(bot.units(SUPPLYDEPOT)) + len(bot.units(SUPPLYDEPOTLOWERED)))
                if len(bot.units(SUPPLYDEPOT)) + len(bot.units(SUPPLYDEPOTLOWERED)) < 3:
                    await self.build_ramp_depots(bot)
                else:
                    print('Looking for a place to build SD')
                    pos = await find_place_to_build(bot, self.agent, SUPPLYDEPOT, buildings_close=[SUPPLYDEPOT, SUPPLYDEPOTLOWERED])
                    print(pos)
                    await bot.do(self.agent.build(SUPPLYDEPOT, pos))
                print('Orders:')
                print(self.agent.orders)
                if self.agent.orders[-1].ability.id == AbilityId.TERRANBUILD_SUPPLYDEPOT:
                    self.state = 'finishing_supply_depot'
            else:
                print('Not ready to build!')
        elif self.state == 'finishing_supply_depot':
            print('Build progress: {}', bot.units(
                SUPPLYDEPOT).closest_to(self.agent).build_progress)
            if bot.units(SUPPLYDEPOT).closest_to(self.agent).build_progress == 1.0:
                print('Finished!')
                self.state = 'building_supply_depot'
        elif self.state == 'building_barracks':
            if self.ready_to_build(AbilityId.TERRANBUILD_BARRACKS) and bot.can_afford(BARRACKS):
                if len(bot.units(BARRACKS)) == 0:
                    print('build barracks')
                    pos = await bot.find_placement(BARRACKS, near=bot.units(COMMANDCENTER).closest_to(self.agent).position)
                    await bot.do(self.agent.build(BARRACKS, pos))
                else:
                    pos = await bot.find_placement(BARRACKS, near=bot.units(BARRACKS).closest_to(self.agent).position)
                    await bot.do(self.agent.build(BARRACKS, pos))
                print('Orders:')
                print(self.agent.orders)
                if self.agent.orders[-1].ability.id == AbilityId.TERRANBUILD_BARRACKS:
                    self.state = 'finishing_barracks'
        elif self.state == 'finishing_barracks':
            print('Build progress: {}', bot.units(
                BARRACKS).closest_to(self.agent).build_progress)
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
        elif self.agent.is_idle and self.state == 'generating_army':
            await bot.do(self.agent.train(MARINE))


class MilitarRole(Role):
    def __init__(self, bot, agent, id_, state='slave'):
        super().__init__(agent, id_, state)

    async def on_step(self, bot, iteration):
        print('Militar {} is {}'.format(self.id, self.state))
        if self.state == 'slave':
            pass
        elif self.state == 'waiting_for_army':
            enemies = close_enemies(bot, self.agent, 50)
            if len(enemies) > 1:
                await bot.do(self.agent.attack(enemies[0]))
                self.state = 'attacking'
            elif len(bot.units(MARINE)) > 50:
                await bot.do(self.agent.attack(bot.enemy_start_locations[0].position))
                self.state = 'attacking'
        elif self.state == 'attacking':
            enemies = close_enemies(bot, self.agent, 50)
            if len(enemies) == 0:
                await bot.do(self.agent.stop())
                self.state = 'waiting_for_army'


class SimpleBot(sc2.BotAI):
    def __init__(self):
        super().__init__()
        # Used to keep track of the time in the last iteration
        self.last_time = time()

        # Bot state (self.state wasn't used because the library already uses it)
        self.state_ = 'first_scvs'

        # Global id used to assign ids to every agent
        self.id_ = 0

        # Agents responsible for gathering resources (SCVs)
        self.gather_agents = []

        # Agents responsible for building SCVs (command centers)
        self.center_agents = []

        # Agents responsible for building structures (SCVs)
        self.build_agents = []

        # Agents responsible for creating militar units (mostly barracks)
        self.army_gen_agents = []

        # Agents responsible for attacking and defending (mostly marines)
        self.militar_agents = []

        # Groups of all agents
        self.roles_groups = [self.gather_agents,
                             self.center_agents,
                             self.build_agents,
                             self.army_gen_agents,
                             self.militar_agents]
        # Agents only do something after this time has passed
        self.time_between_iterations = 0

    def assign_new_units_roles(self):
        # Assign default roles for new units
        # Barracks
        self.army_gen_agents = []
        # old_barracks = [b.agent for b in self.build_agents]
        # new_barracks = [b for b in self.units(
            # BARRACKS) if b not in old_barracks]
        for id_, barracks in enumerate(self.units(BARRACKS)):
            self.army_gen_agents.append(
                ArmyGenRole(self, barracks, self.id_ + id_))
        self.id_ += len(self.units(BARRACKS))

        # Marines
        self.militar_agents = []
        # old_marines = [m.agent for m in self.militar_agents]
        # new_marines = [m for m in self.units(MARINE) if m not in old_marines]
        for id_, marine in enumerate(self.units(MARINE)):
            self.militar_agents.append(
                MilitarRole(self, marine, self.id_ + id_))
            self.militar_agents[-1].state = 'waiting_for_army'
        self.id_ += len(self.units(MARINE))

    async def execute_agents_actions(self, iteration):
        # Execute all agents' actions
        loop = asyncio.get_event_loop()
        tasks = []
        self.roles_groups = [self.gather_agents,
                             self.center_agents,
                             self.build_agents,
                             self.army_gen_agents,
                             self.militar_agents]
        for role_group in self.roles_groups:
            for agent in role_group:
                tasks.append(loop.create_task(
                    agent.on_step(self, iteration)))
        try:
            done, pending = await asyncio.wait(tasks, timeout=2.0)
            for task in pending:
                task.cancel()
            print('End of iteration {}'.format(iteration))
        except:
            print('Skipping iteration...')

    async def on_step(self, iteration):
        # Only does something if it's time to
        if time() - self.last_time > self.time_between_iterations:
            self.last_time = time()

            # Log
            print('Iteration {}'.format(iteration))
            print('Number of gatherers: {}'.format(len(self.gather_agents)))
            print('Number of center: {}'.format(len(self.center_agents)))
            print('Number of build: {}'.format(len(self.build_agents)))
            print('Number of army generators: {}'.format(
                len(self.army_gen_agents)))

            # Initialize roles for units
            if iteration == 0:
                # SCVs are gatherers
                for id_, scv in enumerate(self.units(SCV)):
                    self.gather_agents.append(GatherRole(scv, self.id_ + id_))
                self.id_ += len(self.units(SCV))
                for id_, cc in enumerate(self.units(COMMANDCENTER)):
                    self.center_agents.append(CenterRole(cc, id_))
                self.id_ += len(self.units(COMMANDCENTER))

            # Assign building roles to two SCVs (one builds supply depots and
            # the other builds barracks)
            if self.state_ == 'first_scvs':
                print('Creating first scvs')
                depot_builder = self.gather_agents.pop()
                depot_builder = depot_builder.agent
                barracks_builder = self.gather_agents.pop()
                barracks_builder = barracks_builder.agent
                self.build_agents.append(
                    BuildRole(self, depot_builder, self.id_))
                self.build_agents.append(
                    BuildRole(self, barracks_builder, self.id_ + 1))
                self.id_ += 2
                self.build_agents[-1].state = 'building_supply_depot'
                self.build_agents[-2].state = 'building_barracks'
                self.state_ = 'idle'
            # Don't do anything
            elif self.state_ == 'idle':
                pass

            self.assign_new_units_roles()

            # Lower all supply depots to make locomotion easier
            for sd in self.units(SUPPLYDEPOT).ready:
                await self.do(sd(MORPH_SUPPLYDEPOT_LOWER))

            await self.execute_agents_actions(iteration)


def main():
    sc2.run_game(sc2.maps.get("Abyssal Reef LE"), [
        Bot(Race.Terran, SimpleBot()),
        Computer(Race.Random, Difficulty.Hard)
    ], realtime=False, game_time_limit=(20 * 60))


if __name__ == '__main__':
    main()
