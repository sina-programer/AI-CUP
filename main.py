from collections import namedtuple
from src import game
import itertools
import operator
import random


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
MAIN_NEIGHBORS = None
MAIN_NODE_FORMER = None

Node = namedtuple('Node', ['id', 'score'])
id_getter = operator.attrgetter('id')
score_getter = operator.attrgetter('score')

def node_constructor(node_id, score):
    """ Create 'Node' objects by receiving parameters """

    return Node(node_id, score)

def node_constructor_packed(params):
    """ Create 'Node' objects by packed (zipped) values """

    return node_constructor(*params)

def initialize_player_id(game):
    global PLAYER_ID
    PLAYER_ID = game.get_player_id()['player_id']

def initialize_fort_node(game):
    global FORT_NODE, MAIN_NODE, MAIN_NEIGHBORS, MAIN_NODE_FORMER

    adjacents = keys_to_int(game.get_adj())
    my_strategic_nodes = get_strategic_nodes(game, player_id=PLAYER_ID)
    FORT_NODE = my_strategic_nodes[0].id
    MAIN_NODE = my_strategic_nodes[1].id
    MAIN_NEIGHBORS = adjacents[MAIN_NODE]
    MAIN_NODE_FORMER = MAIN_NODE

def get_player_turn(turn):
    return ((turn-1)  // PLAYERS) + 1

def keys_to_int(dic):
    """ Convert type of keys in input dictionary to integer """

    return {int(key): value for key, value in dic.items()}

def get_main_alternative(game):
    troops_count = keys_to_int(game.get_number_of_troops())
    alternative = random.choice(MAIN_NEIGHBORS)
    alternative_troops = troops_count[alternative]
    for node in MAIN_NEIGHBORS:
        node_troops = troops_count[node]
        if node_troops > alternative_troops:
            alternative = node
            alternative_troops = node_troops

    return alternative

def get_boundary_nodes(game, node_id):
    owners = keys_to_int(game.get_owners())
    adjacents = keys_to_int(game.get_adj())
    checked_nodes = set()
    boundaries = []

    neighbors = adjacents[node_id]
    while neighbors:
        own_neighbors = list(filter(lambda i: owners[i] == PLAYER_ID, neighbors))
        new_neighbors = []

        for node in own_neighbors:
            if node not in checked_nodes:
                checked_nodes.add(node)
                node_neighbors = adjacents[node]
                new_neighbors.extend(node_neighbors)

                if any(list(map(lambda x: owners[x] != PLAYER_ID, node_neighbors))):
                    boundaries.append(node)

        neighbors = list(set(new_neighbors))

    return boundaries

def get_neighbors(game, node_id, max_level=0, flat=False):
    adjacents = keys_to_int(game.get_adj())
    checked_nodes = set()
    neighbors = {}
    level = 1

    checking_nodes = adjacents[node_id]
    while (level <= max_level) and checking_nodes:
        neighbors[level] = checking_nodes
        new_checking_nodes = []

        for i in checking_nodes:
            if i not in checked_nodes:
                checked_nodes.add(i)
                new_checking_nodes.extend(set(adjacents[i]) - checked_nodes)

        checking_nodes = list(set(new_checking_nodes))
        level += 1

    if flat:
        return list(itertools.chain.from_iterable(neighbors.values()))

    return neighbors

def get_strategic_nodes(game, sort=True, reverse=True, player_id=None):
    """ Return all the strategic nodes as 'Node' objects. They also can be ordered by setting parameters """

    strategic_nodes_data = game.get_strategic_nodes()  # fetch strategic nodes data
    strategic_nodes_ = strategic_nodes_data['strategic_nodes']
    scores_ = strategic_nodes_data['score']
    strategic_nodes = list(map(node_constructor_packed, zip(strategic_nodes_, scores_)))  # create a list of Node objects
    if sort:
        strategic_nodes.sort(key=lambda node: node.score, reverse=reverse)  # sort final nodes, by considering parameters
    if player_id is not None:
        owners = keys_to_int(game.get_owners())
        strategic_nodes = list(filter(lambda node: owners[node.id] == player_id, strategic_nodes))
    return strategic_nodes


def initializer(game: game.Game): 
    """ Handle the initialization phase """

    turn = game.get_turn_number()['turn_number']
    player_turn = get_player_turn(turn)

    if not PLAYER_ID:
        initialize_player_id(game)

    if player_turn == 3:  # after occupying our two strategic nodes
        initialize_fort_node(game)

    print('-'*50)
    print(f'Global Turn:  {turn:<6} Player Turn:  {player_turn:<6} Player ID: {PLAYER_ID}')

    # Define essential variables along the turn
    strategic_nodes = get_strategic_nodes(game)
    strategic_nodes_ = list(map(id_getter, strategic_nodes))
    troops_count = keys_to_int(game.get_number_of_troops())
    owners = keys_to_int(game.get_owners())
    my_nodes = [node for node, owner in owners.items() if owner == PLAYER_ID]
    my_strategic_nodes = list(filter(lambda i: i in strategic_nodes_, my_nodes))
    my_ordinary_nodes = list(filter(lambda i: i not in my_strategic_nodes, my_nodes))
    print('Nodes: ', len(my_nodes))

    # first check for empty strategic nodes
    for i in strategic_nodes_:
        if owners[i] == -1:
            print(game.put_one_troop(i))
            return

    # First, occupy empty planets
    if len(my_ordinary_nodes) < MAXIMUM_INITIAL_ORDINARY_NODES:
        for neighbor in get_neighbors(game, MAIN_NODE, flat=True):
            if owners[neighbor] == -1:
                print(game.put_one_troop(neighbor))
                return

    # Next, occupy empty planets
    for neighbor in get_neighbors(game, FORT_NODE, max_level=1, flat=True):
        if owners[neighbor] == -1:
            print(game.put_one_troop(neighbor))
            return

    # boost the boundary
    for boundary_node in get_boundary_nodes(game, MAIN_NODE):
        if troops_count[boundary_node] < BOUNDARY_TROOPS:
            print(game.put_one_troop(boundary_node))
            return

    # put on strategics
    if troops_count[MAIN_NODE] < MAIN_NODE_TROOPS:
        print(game.put_one_troop(MAIN_NODE))
        return

    # Finally, put troops on strategic nodes randomly
    print(game.put_one_troop(FORT_NODE))
    return


def turn(game):
    """ Handle the main phase """

    global BOUNDARY_TROOPS, MAIN_NODE, MAIN_NEIGHBORS

    turn = game.get_turn_number()['turn_number']
    player_turn = get_player_turn(turn)
    print(f'Global Turn:  {turn:<6} Player Turn:  {player_turn:<6} Player ID: {PLAYER_ID}')

    if player_turn == INITIAL_TURNS+1:
        BOUNDARY_TROOPS += 1

    if all(map(lambda x: x, MAIN_NEIGHBORS)):
        MAIN_NEIGHBORS = get_neighbors(game, MAIN_NODE_FORMER, max_level=2)[2]

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
        if node_troops < BOUNDARY_TROOPS:
            if (reserved_troops := get_reserved_troops(game)):
                print(game.put_troop(node, min(BOUNDARY_TROOPS-node_troops, reserved_troops)))
            else:
                return

    main_boundaries = get_boundary_nodes(game, MAIN_NODE)
    for node in main_boundaries:
        node_troops = troops_count[node]
        if node_troops < BOUNDARY_TROOPS:
            if (reserved_troops := get_reserved_troops(game)):
                print(game.put_troop(node, min(BOUNDARY_TROOPS-node_troops, reserved_troops)))
            else:
                return

    my_nodes = [node for node, owner in owners.items() if owner == PLAYER_ID]
    for node in my_nodes:
        node_troops = troops_count[node]
        if (node not in main_boundaries) and (node_troops < INSIDE_TROOPS):
            if (reserved_troops := get_reserved_troops(game)):
                print(game.put_troop(node, min(INSIDE_TROOPS-node_troops, reserved_troops)))
            else:
                return

    print(game.put_troop(MAIN_NODE, get_reserved_troops(game)//2))

def attack_state(game):
    """ Mange the attack state (2nd state) """

    owners = keys_to_int(game.get_owners())
    troops_count = keys_to_int(game.get_number_of_troops())
    adjacents = keys_to_int(game.get_adj())
    max_troops = 0
    max_node = -1

    for i in owners.keys():
        if owners[i] == PLAYER_ID:
            if troops_count[i] > max_troops:
                max_troops = troops_count[i]
                max_node = i

    for i in adjacents[max_node]:
        if (owners[i] != PLAYER_ID) and (owners[i] != -1):
            print(game.attack(max_node, i, 1, 0.5))
            break

def move_troop_state(game):
    """ Mange the move-troop state (3rd state) """

    owners = keys_to_int(game.get_owners())
    troops_count = keys_to_int(game.get_number_of_troops())
    max_troops = 0
    max_node = -1

    for i in owners.keys():
        if owners[i] == PLAYER_ID:
            if troops_count[i] > max_troops:
                max_troops = troops_count[i]
                max_node = i

    try:
        neighbors = game.get_reachable(max_node)['reachable']
        neighbors.remove(max_node)
        destination = random.choice(neighbors)
        print(game.move_troop(max_node, destination, 1))
    except Exception as error:
        print('Error: ', error)

def fort_state(game):
    """ Mange the fort state (4th state) """

    global FORT_FLAG

    troops_count = keys_to_int(game.get_number_of_troops())
    print(game.fort(FORT_NODE, troops_count[FORT_NODE] - ORDINARY_TROOPS_AFTER_FORTRESS))
    FORT_FLAG = True


def get_reserved_troops(game):
    return game.get_number_of_troops_to_put()['number_of_troops']
