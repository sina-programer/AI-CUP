from collections import namedtuple
from src import game
import operator
import random


Node = namedtuple('Node', ['id', 'score'])
FORT_FLAG = False  # Has the fortress been completed yet?

id_getter = operator.attrgetter('id')
score_getter = operator.attrgetter('score')

def node_constructor(node_id, score):
    return Node(node_id, score)

def keys_to_int(dic):
    return {int(key): value for key, value in dic.items()}


def get_strategic_nodes(game, sort=True, reverse=True):
    strategic_nodes_data = game.get_strategic_nodes()
    strategic_nodes_ = strategic_nodes_data['strategic_nodes']
    scores_ = strategic_nodes_data['score']
    strategic_nodes = list(map(node_constructor, zip(strategic_nodes_, scores_)))
    if sort:
        strategic_nodes.sort(key=lambda node: node.score, reverse=reverse)
    return strategic_nodes


def initializer(game: game.Game):   
    print('-'*50)
    print('Turn: ', game.get_turn_number()['turn_number'])

    strategic_nodes = get_strategic_nodes(game)
    strategic_nodes_ = list(map(id_getter, strategic_nodes))
    player_id = game.get_player_id()['player_id']
    owners = keys_to_int(game.get_owners())
    adjacents = keys_to_int(game.get_adj())
    my_nodes = []

    level = 1
    checked_nodes = set()
    checking_nodes = strategic_nodes_.copy()
    while checking_nodes:
        new_checking_nodes = []

        for i in checking_nodes:
            if i not in checked_nodes:
                checked_nodes.add(i)
                neighbors = adjacents[i]
                new_checking_nodes.extend(set(neighbors) - checked_nodes)
                owner = owners[i]

                if owner in [player_id, -1]:
                    my_nodes.append(i)

                if owner == -1:
                    print(game.put_one_troop(i))
                    return

        checking_nodes = list(set(new_checking_nodes))
        level += 1


    troops_count = keys_to_int(game.get_number_of_troops())
    my_strategic_nodes = list(filter(lambda i: i in strategic_nodes_, my_nodes))
    my_ordinary_nodes = list(filter(lambda i: i not in strategic_nodes_, my_nodes))

    for i in my_strategic_nodes:
        if troops_count[i] < 3:
            print(game.put_one_troop(i))
            return

    i = random.choice(my_ordinary_nodes)
    print(game.put_one_troop(i))
    return


def turn(game):
    print('Turn: ', game.get_turn_number()['turn_number'])

    put_troop_state(game)
    game.next_state()

    attack_state(game)
    game.next_state()

    move_troop_state(game)
    game.next_state()

    if not FORT_FLAG:
        fort_state(game)
    game.next_state()

    print('-'*50)


def put_troop_state(game):
    owners = keys_to_int(game.get_owners())
    player_id = game.get_player_id()['player_id']

    for i in owners.keys():
        if (owners[i] == -1) and game.get_number_of_troops_to_put()['number_of_troops']:
            print(game.put_troop(i, 1))

    list_of_my_nodes = []
    for i in owners.keys():
        if owners[i] == player_id:
            list_of_my_nodes.append(i)

    print(game.put_troop(random.choice(list_of_my_nodes), game.get_number_of_troops_to_put()['number_of_troops']))

def attack_state(game):
    owners = keys_to_int(game.get_owners())
    troop_counts = keys_to_int(game.get_number_of_troops())
    player_id = game.get_player_id()['player_id']
    adjacents = keys_to_int(game.get_adj())
    max_troops = 0
    max_node = -1

    for i in owners.keys():
        if owners[i] == player_id:
            if troop_counts[i] > max_troops:
                max_troops = troop_counts[i]
                max_node = i

    for i in adjacents[max_node]:
        if (owners[i] != player_id) and (owners[i] != -1):
            print(game.attack(max_node, i, 1, 0.5))
            break

def move_troop_state(game):
    owners = keys_to_int(game.get_owners())
    troop_counts = keys_to_int(game.get_number_of_troops())
    player_id = game.get_player_id()['player_id']
    max_troops = 0
    max_node = -1

    for i in owners.keys():
        if owners[i] == player_id:
            if troop_counts[i] > max_troops:
                max_troops = troop_counts[i]
                max_node = i

    try:
        neighbors = game.get_reachable(max_node)['reachable']
        neighbors.remove(max_node)
        destination = random.choice(neighbors)
        print(game.move_troop(max_node, destination, 1))
    except Exception as error:
        print('Error: ', error)

def fort_state(game):
    global FORT_FLAG

    owners = keys_to_int(game.get_owners())
    troop_counts = keys_to_int(game.get_number_of_troops())
    player_id = game.get_player_id()['player_id']
    strategic_nodes = get_strategic_nodes(game)

    for node in strategic_nodes:  # nodes are sorted by score
        if owners[node.id] == player_id:
            print(game.fort(node.id, troop_counts[node.id]-1))
            break

    FORT_FLAG = True
