# Cmpt371Project
Group Project for CMPT 371 @ SFU

images from: https://opengameart.org/ 

For the purposes of testing we change the "SERVER_HOST" variable at the top of client.py to determine the host.
To close the server use "CTRL+c" in the terminal that it is running in.

3 terminals (for server and 2 players):

Terminal 1 (run the server): 
cd ... \Cmpt371Project> `python server.py --players 2`

Terminal 2: (player 1):
cd ... \Cmpt371Project> `python client.py`

Terminal 3: (player 2):
cd ... \Cmpt371Project> `python client.py`

For 3 or 4 players: run server with `python server.py --players n` (*n* = 3 or 4)
and run clients respective to chosen *n*.