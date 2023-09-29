from collections import OrderedDict
from typing import Dict, List
from src import game
import numpy as np
import itertools
import operator
import random
import copy


MAXIMUM_INITIAL_ORDINARY_NODES = 10
MINIMUM_STRATEGY_TROOPS = 4
BOUNDARY_TROOPS = 2  # in first main phase turn, it increases by one (=3)
ORDINARY_TROOPS_AFTER_FORTRESS = 2
ATTACK_FLAG = True  # one turn defend, another turn attack
ATTACK_NODE = None
ATTACK_DEST = None

INITIAL_TURNS = 35
MAIN_TURNS = 20
PLAYERS = 3
PLAYER_ID = None
FORT_FLAG = False  # Has the fortress been completed yet?
FORT_NODE = None
MAIN_NODE = None
MAIN_NODE_FORMER = None  # the original main node
MAP : Dict[int, Dict[int, List[int]]] = dict()  # {node: {level: [related neighbors]}}


class Node:
    def __init__(self, node_id, owner=-1, troops=0, fort_troops=0, adjacents=None, score=None):
        self.node_id = node_id
        self.owner = owner
        self.troops = troops
        self.fort_troops = fort_troops
        self.adjacents = adjacents
        self.score = score

    @property
    def is_strategic(self):
        return self.score >= 0

    @property
    def is_mine(self):
        return self.owner == PLAYER_ID

    @property
    def is_empty(self):
        return self.owner == -1

    @property
    def is_enemy(self):
        return self.owner not in [-1, PLAYER_ID]

    @property
    def is_forted(self):
        return self.fort_troops > 0

    def copy(self):
        return copy.copy(self)

    def __repr__(self):
        return f"Node({self.node_id}, owner={self.owner}, troops={self.troops}, fort-troops={self.fort_troops}, score={self.score}, adjacents={self.adjacents})"


class Nodes:
    __slots__ = ['game', 'strategic_nodes', 'fort_troops', 'troops_count', 'adjacents', 'owners', 'nodes', 'name']

    def __init__(self, game, strategic_nodes=None, fort_troops=None, troops_count=None, owners=None, adjacents=None, nodes=None, name=None):
        self.game = game
        self.strategic_nodes = strategic_nodes if strategic_nodes is not None else Nodes.get_strategic_nodes_dict(self.game)
        self.fort_troops = fort_troops if fort_troops is not None else keys_to_int(self.game.get_number_of_fort_troops())
        self.troops_count = troops_count if troops_count is not None else keys_to_int(self.game.get_number_of_troops())
        self.adjacents = adjacents if adjacents is not None else keys_to_int(self.game.get_adj())
        self.owners = owners if owners is not None else keys_to_int(self.game.get_owners())
        self.nodes = nodes if nodes is not None else self.get_nodes()
        self.name = name

    def get_integrated(self, node_id):
        integrated_nodes = []
        for neighbors in MAP[node_id].values():
            integrated_nodes.extend(neighbors)

        return self.filter(is_mine=True, function=lambda node: node.node_id in integrated_nodes, name=self.name+'Integrated')

    def get_boundaries(self, node_id):
        another = self.get_integrated(node_id)
        boundary_nodes = []
        for node in another():
            for adj in self.by_ids(node.adjacents):
                if not adj.is_mine:
                    boundary_nodes.append(node)
                    break

        another.nodes = boundary_nodes
        return another

    def get_nodes(self):
        nodes = []
        for i in self.owners:
            nodes.append(
                Node(
                    i,
                    owner=self.owners[i],
                    troops=self.troops_count[i],
                    fort_troops=self.fort_troops[i],
                    adjacents=self.adjacents[i],
                    score=self.strategic_nodes.get(i, -1)
                )
            )

        return nodes

    @staticmethod
    def get_strategic_nodes_dict(game, sort=True, reverse=True, player_id=None):
        """ Return all the strategic nodes as dict. They also can be ordered by setting parameters """

        strategic_nodes_data = game.get_strategic_nodes()
        strategic_nodes = strategic_nodes_data['strategic_nodes']
        strategic_scores = strategic_nodes_data['score']
        strategics_data = list(zip(strategic_nodes, strategic_scores))

        if sort:
            strategics_data.sort(key=lambda x: x[1], reverse=reverse)
        if player_id is not None:
            owners = keys_to_int(game.get_owners())
            strategics_data = list(filter(lambda x: owners[x[0]] == player_id, strategics_data))

        return OrderedDict(strategics_data)

    def get_attribute(self, attribute):
        return list(map(operator.attrgetter(attribute), self.nodes))

    def find_paths(self, start, stop, path=[], player_id=None):
        path += [start]

        if start == stop:
            return [path]

        total_paths = []
        for adj in self.adjacents[start]:
            if adj not in path:
                if (player_id is None) or (self.owner[adj] == player_id):
                    total_paths.extend(self.find_paths(adj, stop, path=path, player_id=player_id))

        return total_paths

    def shortest_path(self, start, stop, player_id=None):
        paths = self.find_paths(start, stop, player_id=player_id)
        if paths:
            return min(paths, key=len)
        return []

    def by_id(self, node_id):
        return self(node_id=node_id)[0]

    def by_ids(self, node_ids):
        for node_id in node_ids:
            yield self.by_id(node_id)

    def filter(self, name=None, **kwargs):
        return self.duplicate(nodes=conditional_getter(self.nodes, **kwargs), name=name if name else self.name+'Filtered')

    def sort(self, key, reverse=True, name=None):
        return self.duplicate(nodes=sorted(self.nodes, key=operator.attrgetter(key), reverse=reverse), name=name if name else self.name+'Sorted')

    def duplicate(self, **kwargs):
        return Nodes(**{
            **self.get_parameters(),
            **kwargs
        })

    def update(self, owner=True, troops=True, fort_troops=True):
        new_data = {
            'owner': keys_to_int(self.game.get_owners()) if owner else None,
            'troops': keys_to_int(self.game.get_number_of_troops()) if troops else None,
            'fort_troops': keys_to_int(self.game.get_number_of_fort_troops()) if fort_troops else None
        }

        for param, values in new_data.items():
            if values:
                for node in self.nodes:
                    setattr(node, param, values[node.node_id])

                if param == 'owner':
                    self.owners = values
                elif param == 'troops':
                    self.troops_count = values
                elif param == 'fort-troops':
                    self.fort_troops = values

    def copy(self):
        return copy.copy(self)

    def get_parameters(self):
        return {
            key: getattr(self, key)
            for key in self.__slots__
        }

    def get_weights(self, node_id, points=3):
        ''' 
        calculate the density of enemies from boundary nodes due to <node_id>
        weight = sum(number-of-enemies * 1/level)
        '''

        weights = {}  # node: weight
        for node in self.get_boundaries(node_id).nodes:
            weight = 0
            level = 1
            checked_nodes = set()
            enemy_neighbors = list(filter(lambda node: not node.is_mine, self.by_ids(node.adjacents)))
            while enemy_neighbors:
                new_enemy_neighbors = []
                for enemy_node in enemy_neighbors:
                    if enemy_node not in checked_nodes:
                        checked_nodes.add(enemy_node)
                        new_enemy_neighbors.extend(list(filter(lambda node: not node.is_mine, self.by_ids(enemy_node.adjacents))))
                        weight += (enemy_node.troops * (1/level))

                enemy_neighbors = list(set(new_enemy_neighbors))
                level += 1

            weights[node.node_id] = trunc(weight, points)

        return weights

    def __contains__(self, node_id):
        return node_id in self.get_attribute('node_id')

    def __len__(self):
        return len(self.nodes)

    def __call__(self, **kwargs):
        return conditional_getter(self.nodes, **kwargs)

    def __repr__(self):
        return f"{self.name if self.name else 'Nodes'}(length={len(self)})"


def initialize_player_id(game):
    global PLAYER_ID
    PLAYER_ID = game.get_player_id()['player_id']

def initialize_map(game, level):
    global MAP

    adjacents = keys_to_int(game.get_adj())
    for node_id in adjacents:
        if level == 1:
            MAP[node_id] = {
                0: [node_id],
                1: adjacents[node_id]
            }

        else:
            neighbors = set()
            for neighbor in MAP[node_id][level-1]:
                neighbors = neighbors.union(adjacents[neighbor])
            neighbors -= set(MAP[node_id][level-1] + MAP[node_id][level-2])
            MAP[node_id][level] = list(neighbors)

def conditional_getter(objects, function=None, **conditions):
    if function:
        objects = list(filter(function, objects))

    return list(filter(lambda obj: all(getattr(obj, key) == value for key, value in conditions.items()), objects))

def get_player_turn(turn):
    return ((turn-1)  // PLAYERS) + 1

def keys_to_int(dic):
    """ Convert type of keys in input dictionary to integer """

    return {int(key): value for key, value in dic.items()}

def invert_dict(dic):
    return {value: key for key, value in dic.items()}

def trunc(number, points=2):
    coef = 10 ** points
    return int(number * coef) / coef

def normalize(numbers):
    minimum = np.min(numbers)
    maximum = np.max(numbers)
    return (numbers - minimum) / (maximum - minimum)

def softmax(x):
    x = np.array(x)
    e_x = np.exp(x - np.max(x))  # Subtracting np.max(x) for numerical stability
    return e_x / e_x.sum(axis=0)

def get_reserved_troops(game):
    return game.get_number_of_troops_to_put()['number_of_troops']


def initializer(game: game.Game):
    """ Handle the initialization phase """

    global FORT_NODE, MAIN_NODE, MAIN_NODE_FORMER

    turn = game.get_turn_number()['turn_number']
    player_turn = get_player_turn(turn)

    if not PLAYER_ID:
        initialize_player_id(game)

    initialize_map(game, level=player_turn)

    print('-'*50)
    print(f'Global Turn:  {turn:<6} Player Turn:  {player_turn:<6} Player ID: {PLAYER_ID}')

    nodes = Nodes(game, name='EntireNodes')

    if FORT_NODE is None:
        FORT_NODE = nodes.sort(key='score')(is_strategic=True, is_empty=True)[0].node_id
        print(game.put_one_troop(FORT_NODE))
        return

    if MAIN_NODE is None:
        strategic_nodes = nodes(is_strategic=True, is_empty=True)
        for node in strategic_nodes:
            node.path = nodes.shortest_path(FORT_NODE, node.node_id)
        MAIN_NODE = min(strategic_nodes, key=lambda node: len(node.path)).node_id
        MAIN_NODE_FORMER = MAIN_NODE
        print(game.put_one_troop(MAIN_NODE))
        return

    if len(nodes.filter(is_mine=True, is_strategic=False)) < MAXIMUM_INITIAL_ORDINARY_NODES:
        for neighbors in MAP[MAIN_NODE].values():
            for node in nodes.by_ids(neighbors):
                if node.is_empty:
                    print(game.put_one_troop(node.node_id))
                    return

    for node in nodes.by_ids(MAP[FORT_NODE][1]):
        if node.is_empty:
            print(game.put_one_troop(node.node_id))
            return

    for node in nodes.get_boundaries(MAIN_NODE)():
        if node.troops < BOUNDARY_TROOPS:
            print(game.put_one_troop(node.node_id))
            return

    for node in nodes(is_strategic=True, is_mine=True):
        if node.troops < MINIMUM_STRATEGY_TROOPS:
            print(game.put_one_troop(node.node_id))
            return

    print(game.put_one_troop(FORT_NODE))
    return


def turn(game):
    """ Handle the main phase """

    global BOUNDARY_TROOPS, MAIN_NODE, FORT_FLAG, ATTACK_FLAG, ATTACK_NODE, ATTACK_DEST
    ATTACK_FLAG = not ATTACK_FLAG

    turn = game.get_turn_number()['turn_number']
    player_turn = get_player_turn(turn)
    print(f'Global Turn:  {turn:<6} Player Turn:  {player_turn:<6} Player ID: {PLAYER_ID}')

    nodes = Nodes(game, name='EntireNodes')

    if player_turn == INITIAL_TURNS+1:
        BOUNDARY_TROOPS += 1

    if nodes.owners[MAIN_NODE] == PLAYER_ID:
        MAIN_NODE = MAIN_NODE_FORMER
    else:
        new_node_id = None
        for campus in [MAIN_NODE_FORMER, FORT_NODE]:
            for neighbors in MAP[campus].values():
                for neighbor in nodes.by_ids(neighbors):
                    if neighbor.is_mine:
                        new_node_id = neighbor.node_id

        if new_node_id is None:
            new_node_id = nodes.filter(is_mine=True).sort('troops')()[0].node_id

        if new_node_id is not None:
            MAIN_NODE = nodes.get_integrated(new_node_id).sort('troops')()[0].node_id
        else:
            return


    # put-troop state ----------------------------------
    put_empty_strategics(game, nodes)
    nodes.update()

    if ATTACK_FLAG:
        put_troop_attacker(game, nodes)
    else:
        put_troop_defender(game, nodes)

    to_state(game, 2)
    nodes.update()


    # attack state -------------------------------------
    if ATTACK_FLAG:
        if ATTACK_NODE is not None:
            while True:
                attack_node = nodes.by_id(ATTACK_NODE)
                if attack_node.troops < 3:
                    break

                if ATTACK_DEST is None:
                    if player_turn >= INITIAL_TURNS+MAIN_TURNS-5:  # last turns
                        strategy_dest = nodes.filter(is_strategic=True, is_enemy=True, is_forted=False).sort(key='troops')()[0]
                        path = nodes.shortest_path(ATTACK_NODE, strategy_dest)
                        if len(path) <= 2:
                            break

                        ATTACK_DEST = path[1].node_id

                    else:
                        neighbors = list(filter(lambda node: node.is_enemy, nodes.by_ids(attack_node.adjacents)))
                        if neighbors:
                            ATTACK_DEST = min(neighbors, key=lambda node: node.troops).node_id
                        else:
                            break

                response = game.attack(ATTACK_NODE, ATTACK_DEST, .95, .9)
                print(response)
                if attack_node.is_strategic or response['won']==0:
                    break

                ATTACK_NODE = ATTACK_DEST
                ATTACK_DEST = None

        ATTACK_NODE = None
        ATTACK_DEST = None

    to_state(game, 3)


    # move-troop state ---------------------------------
    if ATTACK_FLAG:
        for node in nodes.get_boundaries(MAIN_NODE)(function=lambda n: n.troops<BOUNDARY_TROOPS):
            put_troops = BOUNDARY_TROOPS - node.troops
            mine_neighbors = list(filter(lambda node: node.is_mine, nodes.by_ids(node.adjacents)))
            if mine_neighbors:
                origin_node = random.choice(mine_neighbors)
                if origin_node.troops >= 3:
                    print(game.move_troop(origin_node.node_id, node.node_id, min(put_troops, origin_node.troops)))
                    nodes.update(owner=False, fort_troops=False)
                    break

    to_state(game, 4)


    # fort state ---------------------------------------
    fort_node = nodes.by_id(FORT_NODE)
    if (not FORT_FLAG) and fort_node.is_mine:
        print(game.fort(fort_node.node_id, fort_node.troops - ORDINARY_TROOPS_AFTER_FORTRESS))
        FORT_FLAG = True

    to_state(game, 5)

    print('-'*50)


def to_state(game, state):
    if game.get_state()['state'] == state-1:
        game.next_state()

def is_state(game, state):
    if game.get_state()['state'] == state:
        return True

def check_boundary_troops(game, nodes, node_id):
    for node in nodes.get_boundaries(node_id)(function=lambda node: node.troops<BOUNDARY_TROOPS):
        put_troops = BOUNDARY_TROOPS - node.troops
        if (reserved_troops := get_reserved_troops(game)) >= 1:
            print(game.put_troop(node.node_id, min(put_troops, reserved_troops)))
        else:
            to_state(game, 2)
            break

        nodes.update(owner=False, fort_troops=False)

def check_tortoise_defense(game, nodes, node_id):
    for level in range(30, 0, -1):
        for neighbor in nodes.by_ids(MAP[node_id][level]):
            if neighbor.is_mine:
                put_troops = int(level*1.5)+1 - neighbor.troops
                if put_troops >= 1:
                    if (reserved_troops := get_reserved_troops(game)) >= 1:
                        print(game.put_troop(neighbor.node_id, min(put_troops, reserved_troops)))
                    else:
                        to_state(game, 2)
                        return

                    nodes.update(owner=False, fort_troops=False)

def check_dense_enemies(game, nodes, node_id):
    node_weight = nodes.get_weights(node_id)
    weights_ = list(node_weight.values())
    nodes_ = list(node_weight.keys())
    weights_mean = np.mean(weights_)
    qualified_weights = list(filter(lambda x: x >= weights_mean, weights_))

    reserved_troops = get_reserved_troops(game)
    nodes_count = len(qualified_weights)
    if nodes_count > reserved_troops:
        nodes_count = reserved_troops
    node_troops = reserved_troops // nodes_count

    for node_id in sorted(nodes_, key=lambda node: node_weight[node], reverse=True)[:nodes_count]:
        print(game.put_troop(node_id, node_troops))

    nodes.update(owner=False, fort_troops=False)

def put_empty_strategics(game, nodes):
    for node in nodes(is_strategic=True, is_empty=True):
        if (reserved_troops := get_reserved_troops(game)) >= 1:
            print(game.put_troop(node.node_id, min(MINIMUM_STRATEGY_TROOPS, reserved_troops)))
            nodes.update(fort_troops=False)
        else:
            to_state(game, 2)
            return

def put_empty_nodes(game, nodes, node_id):
    empty_nodes = nodes(is_empty=True)
    for node in empty_nodes:
        node.path = nodes.shortest_path(node_id, node.node_id)
    for node in sorted(empty_nodes, key=lambda node: len(node.path)):
        if (reserved_troops := get_reserved_troops(game)) >= 1:
            print(game.put_troop(node.node_id, min(1, reserved_troops)))
            nodes.update(fort_troops=False)
        else:
            to_state(game, 2)
            return


def put_troop_defender(game, nodes):
    check_boundary_troops(game, nodes, MAIN_NODE)

    if is_state(game, 1):
        check_boundary_troops(game, nodes, FORT_NODE)

    if is_state(game, 1):
        check_tortoise_defense(game, nodes, MAIN_NODE)

    if is_state(game, 1):
        check_dense_enemies(game, nodes, MAIN_NODE)

    if is_state(game, 1):
        put_empty_nodes(game, nodes, MAIN_NODE)

def put_troop_attacker(game, nodes):
    check_loose_strategics(game, nodes)

    if is_state(game, 1):
        check_low_enemies(game, nodes, FORT_NODE)

def check_loose_strategics(game, nodes):
    global ATTACK_NODE, ATTACK_DEST

    for node in nodes.filter(is_strategic=True, is_enemy=True).sort(key='score')():
        for adj in nodes.by_ids(node.adjacents):
            if adj.is_empty:
                reserved_troops = get_reserved_troops(game)
                ATTACK_NODE = adj.node_id
                ATTACK_DEST = node.node_id
                print(game.put_troop(ATTACK_NODE, reserved_troops))

                to_state(game, 3)
                return ATTACK_NODE

def check_low_enemies(game, nodes, node_id):
    global ATTACK_NODE

    node_weight = nodes.get_weights(node_id)
    weight_node = invert_dict(node_weight)

    least_weight = min(node_weight.values())
    least_node = weight_node[least_weight]
    ATTACK_NODE = least_node

    reserved_troops = get_reserved_troops(game)
    print(game.put_troop(ATTACK_NODE, reserved_troops-2))
    to_state(game, 3)

    return ATTACK_NODE
