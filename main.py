from collections import OrderedDict
from typing import Dict, List
from src import game
import itertools
import operator
import random
import copy


MAXIMUM_INITIAL_ORDINARY_NODES = 10
MAIN_NODE_TROOPS = 4
BOUNDARY_TROOPS = 2  # in first main phase turn, it increases by one (=3)
INSIDE_TROOPS = 2
ORDINARY_TROOPS_AFTER_FORTRESS = 2

INITIAL_TURNS = 35
MAIN_TURNS = 20
PLAYERS = 3
PLAYER_ID = None
FORT_FLAG = False  # Has the fortress been completed yet?
FORT_NODE = None
MAIN_NODE = None
MAIN_NODE_FORMER = None  # the original main node
MAP : Dict[int, Dict[int, List[int]]] = {}  # {node: {level: [related neighbors]}}


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
        return self.score is not None

    @property
    def is_mine(self):
        return self.owner == PLAYER_ID

    @property
    def is_forted(self):
        return self.fort_troops > 0

    def copy(self):
        return copy.copy(self)

    def __repr__(self):
        return f"Node(owner={self.owner}, troops={self.troops}, fort-troops={self.fort_troops}, adjacents={self.adjacents}, score={self.score})"


class Nodes:
    def __init__(self, game, nodes=None, name=None):
        self.game = game
        self.nodes = nodes if nodes else Nodes.get_nodes(self.game)
        self.name = name

    def get_integrated(self, node_id):
        integrated_nodes = []
        for neighbors in MAP[node_id].values():
            integrated_nodes.extend(neighbors)

        return self.filter(owner=PLAYER_ID, function=lambda node: node.node_id in integrated_nodes)

    def get_boundaries(self, node_id):
        another = self.get_integrated(node_id)
        boundary_nodes = []

        for node in another():
            for adj_id in node.adjacents:
                adj_node = self.by_id(adj_id)
                if adj_node.owner != PLAYER_ID:
                    boundary_nodes.append(node)
                    break

        another.nodes = boundary_nodes
        return another

    @classmethod
    def get_nodes(cls, game):
        strategic_nodes = Nodes.get_strategic_nodes_dict(game)
        fort_troops = keys_to_int(game.get_number_of_fort_troops())
        troops_count = keys_to_int(game.get_number_of_troops())
        adjacents = keys_to_int(game.get_adj())
        owners = keys_to_int(game.get_owners())
        nodes = []

        for i in owners:
            nodes.append(
                Node(
                    i,
                    owner=owners[i],
                    troops=troops_count[i],
                    fort_troops=fort_troops[i],
                    adjacents=adjacents[i],
                    score=strategic_nodes.get(i, None)
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

    def filter(self, name=None, **kwargs):
        return Nodes(self.game, nodes=conditional_getter(self.nodes, **kwargs), name=name)

    def get_attribute(self, attribute):
        return list(map(operator.attrgetter(attribute), self.nodes))

    def by_id(self, node_id):
        return self(node_id=node_id)[0]

    def copy(self):
        return copy.copy(self)

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

def initialize_fort_node(game):
    global FORT_NODE, MAIN_NODE, MAIN_NODE_FORMER

    adjacents = keys_to_int(game.get_adj())
    my_strategic_nodes = Nodes.get_strategic_nodes_dict(game, player_id=PLAYER_ID)
    my_strategic_nodes_ = list(my_strategic_nodes.keys())
    FORT_NODE = my_strategic_nodes_[0]
    MAIN_NODE = my_strategic_nodes_[1]
    MAIN_NODE_FORMER = MAIN_NODE

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
            MAP[node_id][level] = sorted(list(neighbors))

def conditional_getter(objects, function=None, **conditions):
    if function:
        objects = list(filter(function, objects))

    return list(filter(lambda obj: all(getattr(obj, key) == value for key, value in conditions.items()), objects))

def get_player_turn(turn):
    return ((turn-1)  // PLAYERS) + 1

def keys_to_int(dic):
    """ Convert type of keys in input dictionary to integer """

    return {int(key): value for key, value in dic.items()}

def get_reserved_troops(game):
    return game.get_number_of_troops_to_put()['number_of_troops']


def initializer(game: game.Game): 
    """ Handle the initialization phase """

    turn = game.get_turn_number()['turn_number']
    player_turn = get_player_turn(turn)

    if not PLAYER_ID:
        initialize_player_id(game)

    if player_turn == 3:  # after occupying our two strategic nodes
        initialize_fort_node(game)

    initialize_map(game, level=player_turn)

    print('-'*50)
    print(f'Global Turn:  {turn:<6} Player Turn:  {player_turn:<6} Player ID: {PLAYER_ID}')

    nodes = Nodes(game, name='EntireNodes')
    my_nodes = nodes.filter(is_mine=True, name='MyNodes')
    strategic_nodes = nodes.filter(is_strategic=True, name='StrategicNodes')
    my_ordinary_nodes = my_nodes.filter(is_strategic=False, name='MyOrdinaryNodes')

    # first check for empty strategic nodes
    for node in strategic_nodes(owner=-1):
        print(game.put_one_troop(node.node_id))
        return

    # First, occupy empty planets
    if len(my_ordinary_nodes) < MAXIMUM_INITIAL_ORDINARY_NODES:
        for neighbors in MAP[MAIN_NODE].values():
            for neighbor in neighbors:
                node = nodes.by_id(neighbor)
                if node.owner == -1:
                    print(game.put_one_troop(node.node_id))
                    return

    # Next, occupy empty planets
    for neighbor in MAP[FORT_NODE][1]:
        node = nodes.by_id(neighbor)
        if node.owner == -1:
            print(game.put_one_troop(node.node_id))
            return

    # boost the boundary
    for node in nodes.get_boundaries(MAIN_NODE)():
        if node.troops < BOUNDARY_TROOPS:
            print(game.put_one_troop(node.node_id))
            return

    # put on strategics
    node = my_nodes.by_id(MAIN_NODE)
    if node.troops < MAIN_NODE_TROOPS:
        print(game.put_one_troop(node.node_id))
        return

    # Finally, put troops on strategic nodes randomly
    print(game.put_one_troop(FORT_NODE))
    return


def turn(game):
    """ Handle the main phase """

    global BOUNDARY_TROOPS, MAIN_NODE

    turn = game.get_turn_number()['turn_number']
    player_turn = get_player_turn(turn)
    print(f'Global Turn:  {turn:<6} Player Turn:  {player_turn:<6} Player ID: {PLAYER_ID}')

    if player_turn == INITIAL_TURNS+1:
        BOUNDARY_TROOPS += 1

    owners = keys_to_int(game.get_owners())
    if owners[MAIN_NODE] == PLAYER_ID:
        MAIN_NODE = MAIN_NODE_FORMER
    else:
        MAIN_NODE = get_main_alternative(game)

    put_troop_state(game)
    game.next_state()

    attack_state(game)
    game.next_state()

    move_troop_state(game)
    game.next_state()

    if (not FORT_FLAG) and (owners[FORT_NODE] == PLAYER_ID):
        fort_state(game)
    game.next_state()

    print('-'*50)


def put_troop_state(game):
    """ Manage the put-troop state (1st state) """

    troops_count = keys_to_int(game.get_number_of_troops())
    owners = keys_to_int(game.get_owners())

    for node in get_boundary_nodes(game, FORT_NODE):
        node_troops = troops_count[node]
        put_troops = BOUNDARY_TROOPS - node_troops
        if put_troops >= 1:
            if (reserved_troops := get_reserved_troops(game)) >= 1:
                print(game.put_troop(node, min(put_troops, reserved_troops)))
            else:
                return

    main_boundaries = get_boundary_nodes(game, MAIN_NODE)
    for node in main_boundaries:
        node_troops = troops_count[node]
        put_troops = BOUNDARY_TROOPS - node_troops
        if put_troops >= 1:
            if (reserved_troops := get_reserved_troops(game)) >= 1:
                print(game.put_troop(node, min(put_troops, reserved_troops)))
            else:
                return

    my_nodes = [node for node, owner in owners.items() if owner == PLAYER_ID]
    for node in my_nodes:
        node_troops = troops_count[node]
        put_troops = BOUNDARY_TROOPS - node_troops
        if put_troops >= 1:
            if (reserved_troops := get_reserved_troops(game)) >= 1:
                print(game.put_troop(node, min(put_troops, reserved_troops)))
            else:
                return

    if (reserved_troops := get_reserved_troops(game)) >= 1:
        print(game.put_troop(origin_node, min(troops, reserved_troops)))

def attack_state(game):
    """ Manage the attack state (2nd state) """

    owners = keys_to_int(game.get_owners())
    troops_count = keys_to_int(game.get_number_of_troops())
    adjacents = keys_to_int(game.get_adj())

    for boundary_node in get_boundary_nodes(game, MAIN_NODE):
        neighbors = adjacents[boundary_node]
        enemy_neighbors = list(filter(lambda n: owners[n] not in [-1, PLAYER_ID], neighbors))
        enemy_node = sorted(enemy_neighbors, key=lambda n: troops_count[n])[-1]
        print(game.attack(boundary_node, enemy_node, .95, .5))
        return

def move_troop_state(game):
    """ Mange the move-troop state (3rd state) """

    troops_count = keys_to_int(game.get_number_of_troops())

    for boundary_node in get_boundary_nodes(game, MAIN_NODE):
        node_troops = troops_count[boundary_node]
        put_troops = BOUNDARY_TROOPS - node_troops
        if put_troops >= 1:
            if (reserved_troops := troops_count[MAIN_NODE]) >= 1:
                print(game.move_troop(MAIN_NODE, boundary_node, min(put_troops, reserved_troops)))
            else:
                return

def fort_state(game):
    """ Mange the fort state (4th state) """

    global FORT_FLAG

    troops_count = keys_to_int(game.get_number_of_troops())
    print(game.fort(FORT_NODE, troops_count[FORT_NODE] - ORDINARY_TROOPS_AFTER_FORTRESS))
    FORT_FLAG = True
