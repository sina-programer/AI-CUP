from collections import namedtuple
from src import game
import random


Node = namedtuple('Node', ['id', 'score'])
game.flag = False


def keys_to_int(dic):
    return {int(key): value for key, value in dic.items()}

def put_one_troop(game, i, description=None):
    response = game.put_one_troop(i)
    print(f"One troop put in id={i}" + f" ({description})" if description else '')
    print(response)

def get_strategic_nodes(game):
    strategic_nodes_ = game.get_strategic_nodes()['strategic_nodes']
    scores_ = game.get_strategic_nodes()['score']
    strategic_nodes = list(map(lambda x: Node(*x), zip(strategic_nodes_, scores_)))
    strategic_nodes.sort(key=lambda node: node.score, reverse=True)
    return strategic_nodes


def initializer(game: game.Game):   
    print('-'*50)
    print('Turn: ', game.get_turn_number()['turn_number'])

    strategic_nodes = get_strategic_nodes(game)
    strategic_nodes_ = list(map(lambda node: node.id, strategic_nodes))
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
                    put_one_troop(game, i, description=f"level={level}")
                    return

        checking_nodes = list(set(new_checking_nodes))
        level += 1


    troops_count = keys_to_int(game.get_number_of_troops())
    my_strategic_nodes = list(filter(lambda i: i in strategic_nodes_, my_nodes))
    my_ordinary_nodes = list(filter(lambda i: i not in strategic_nodes_, my_nodes))

    for i in my_strategic_nodes:
        if troops_count[i] < 3:
            put_one_troop(game, i, description=f'strategic randomly')
            return

    i = random.choice(my_ordinary_nodes)
    put_one_troop(game, i, description=f'ordinary randomly')
    return


def turn(game):
    print(game.get_number_of_troops_to_put())
    owner = game.get_owners()
    for i in owner.keys():
        if owner[str(i)] == -1 and game.get_number_of_troops_to_put()['number_of_troops'] > 1:
            print(game.put_troop(i, 1))
            
    list_of_my_nodes = []
    for i in owner.keys():
        if owner[str(i)] == game.get_player_id()['player_id']:
            list_of_my_nodes.append(i)
    print(game.put_troop(random.choice(list_of_my_nodes), game.get_number_of_troops_to_put()['number_of_troops']))
    print(game.get_number_of_troops_to_put())

    print(game.next_state())

    # find the node with the most troops that I own
    max_troops = 0
    max_node = -1
    owner = game.get_owners()
    for i in owner.keys():
        if owner[str(i)] == game.get_player_id()['player_id']:
            if game.get_number_of_troops()[i] > max_troops:
                max_troops = game.get_number_of_troops()[i]
                max_node = i
    # find a neighbor of that node that I don't own
    adj = game.get_adj()
    for i in adj[max_node]:
        if owner[str(i)] != game.get_player_id()['player_id'] and owner[str(i)] != -1:
            print(game.attack(max_node, i, 1, 0.5))
            break
    print(game.next_state())
    print(game.get_state())
    # get the node with the most troops that I own
    max_troops = 0
    max_node = -1
    owner = game.get_owners()
    for i in owner.keys():
        if owner[str(i)] == game.get_player_id()['player_id']:
            if game.get_number_of_troops()[i] > max_troops:
                max_troops = game.get_number_of_troops()[i]
                max_node = i
    print(game.get_reachable(max_node))
    destination = random.choice(game.get_reachable(max_node)['reachable'])
    print(game.move_troop(max_node, destination, 1))
    print(game.next_state())

    if flag == False:
        max_troops = 0
        max_node = -1
        owner = game.get_owners()
        for i in owner.keys():
            if owner[str(i)] == game.get_player_id()['player_id']:
                if game.get_number_of_troops()[i] > max_troops:
                    max_troops = game.get_number_of_troops()[i]
                    max_node = i

        print(game.get_number_of_troops()[str(max_node)])
        print(game.fort(max_node, 3))
        print(game.get_number_of_fort_troops())
        flag = True
