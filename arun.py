import os
import shutil

filename = 'main.py'
path = r"Kernel-faster-for-python"
players = ['player0', 'player1', 'player2']

for player in players:
	player_path = os.path.join(path, player, filename)
	os.remove(player_path)
	shutil.copy(filename, player_path)

print(f"All {filename} file(s) are copied! \n")

os.system(f"python {os.path.join(path, 'run.py')}")

input("Press enter to exit...")
