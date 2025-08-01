import socket
import threading
import json
import random
import time
import argparse

# --------------------------------------------------------------------------------------------------------------------------------
#  Server Configuration  
# ------------------------------------------------------------------------------------------------------------------------------
# Host and port where the server will listen for incoming connections.
SERVER_HOST = '0.0.0.0'  # Listen on all network interfaces
SERVER_PORT = 12345      # Clients will connect to this port
MIN_PLAYERS = 2          # Minimum number of players required to start
MAX_PLAYERS = 4          # Maximum players allowed in a single game

# -------------------------------------------------------------------------------------------------------------------------------
#  Tracking Connections   
# ---------------------------------------------------------------------------------------------------------------------------------
# We'll keep a list of all connected clients (connection, address, player_id)
connected_clients = []
clients_lock = threading.RLock()


def parse_args():
    """
    Read command-line arguments so we can set the number of players (2-4).
    """
    parser = argparse.ArgumentParser(description='Memory Card Game Server')
    parser.add_argument(
        '--players', '-p',
        type=int,
        choices=range(MIN_PLAYERS, MAX_PLAYERS+1),
        default=MIN_PLAYERS,
        help='How many players will join the game (2-4)'
    )
    return parser.parse_args()

# ---------------------------------------------------------------------------------------------------------------------
#  Game State (protected by a lock)    
# ---------------------------------------------------------------------------------------------------------------------
card_deck = []            # Our shuffled pairs of cards
faceup_cards = []         # Which cards are currently faceup
matched_cards = []        # Which cards have been permanently matched
player_scores = {}        # How many pairs each player has found
current_player_index = 0  # Whose turn it is 
first_flipped_card = None # Remember the first flip to compare it on the second flip
is_game_started = False  
per_card_locks = []       # A lock for each individual card to prevent race conditions
game_state_lock = threading.Lock()

# -------------------------------------------------------------------------------------------------------------------
#  Networking Helper Functions   
# ------------------------------------------------------------------------------------------------------------------

def broadcast_message(message):
    global clients_lock
    print("[DEBUG] broadcast_message() called with message:") 
    print(message)
    with clients_lock:
        print(f"[DEBUG] Currently {len(connected_clients)} connected clients")
        for client_conn, _, _ in connected_clients:
            print("[DEBUG] Sending message to a client")
            send_message_to_client(client_conn, message)


def send_message_to_client(client_conn, message):
    """
    Send a JSON message to a single client.
    """
    try:
        client_conn.sendall((json.dumps(message) + '\n').encode())
    except BrokenPipeError:
        # Client might have gone away, we can't do much.
        pass

# ----------------------------------------------------------------------------------------------------------------------------
#  Starting the Game                
# -----------------------------------------------------------------------------------------------------------------------------

def start_game():
    print("[DEBUG] start_game() called.") 
    """
    Shuffle the cards, set up locks, pick who goes first, and let everyone know the game is on!
    """
    global card_deck, faceup_cards, matched_cards, player_scores
    global current_player_index, first_flipped_card, is_game_started, per_card_locks

    with game_state_lock:
        # Build and shuffle our deck of 8 pairs (=16 cards)
        num_pairs = 8
        card_deck = list(range(num_pairs)) * 2
        random.shuffle(card_deck)
        # Initially, all cards are face-down and unmatched
        faceup_cards = [False] * len(card_deck)
        matched_cards = [False] * len(card_deck)
        # Give each card its own lock to avoid race conditions on flips
        per_card_locks = [threading.Lock() for _ in card_deck]
        # Everyone starts with zero points
        player_scores = {pid: 0 for _, _, pid in connected_clients}
        # Randomly pick who goes first
        current_player_index = random.randrange(len(connected_clients))
        first_flipped_card = None
        is_game_started = True

    # Let all players know we've starte3d
    broadcast_message({
        "type": "GAME_START",
        "num_cards": len(card_deck),
        "players": [pid for _, _, pid in connected_clients]
    })
    send_turn_notification()

# --------------------------------------------------------------------------------------------------------------------
#  Turn Notification                
# ---------------------------------------------------------------------------------------------------------------------

def send_turn_notification():
    """
    Tell everyone whose turn it is now.
    """
    print("[DEBUG] send_turn_notification() called.") 

    with game_state_lock:
        print("[DEBUG] send_turn_notifications() withGame stateLOCK") 
        player_id = connected_clients[current_player_index][2]
    broadcast_message({
        "type": "YOUR_TURN",
        "player_id": player_id,
        "scores": player_scores
    })

# -------------------------------------------------------------------------------------------------------------------
#  Handling a card Flip             
# -------------------------------------------------------------------------------------------------------------------

def process_flip_request(player_id, card_index, client_conn):
    """
    When a player asks to flip a card:
      - Check turn order
      - Validate that card can be flipped
      - Lock the card, reveal it, compare if it's the second flip
      - Handle matches or mismatches, update scores or change turns
    """
    global first_flipped_card, current_player_index
    is_next_turn = False
    pidx = 0
    with game_state_lock:
        # 1) Make sure it's really this player's turn
        if connected_clients[current_player_index][2] != player_id:
            send_message_to_client(client_conn, {"type": "ERROR", "message": "It's not your turn."})
            return
        # 2) Make sure the chosen card is in range and not already revealed/matched
        if (card_index < 0 or card_index >= len(card_deck) or
            faceup_cards[card_index] or matched_cards[card_index]):
            send_message_to_client(client_conn, {"type": "ERROR", "message": "Cannot flip that card."})
            return
        # 3) Try locking that card so no one else flips it at the same time
        if not per_card_locks[card_index].acquire(blocking=False):
            send_message_to_client(client_conn, {"type": "ERROR", "message": "That card is busy."})
            return
        # 4) Reveal the card to everyone
        faceup_cards[card_index] = True
        card_identity = card_deck[card_index]
        broadcast_message({"type": "CARD_REVEALED", "card_index": card_index, "identity": card_identity})

        # Was this the first flip or the second in this player's turn?
        if first_flipped_card is None:
            # Remember this flip and wait for the next one
            first_flipped_card = (player_id, card_index)
        else:
            prev_pid, prev_index = first_flipped_card
            is_match = (card_deck[prev_index] == card_identity)

            if is_match:
                # Great! Those two cards stay face-up and count for a point
                matched_cards[prev_index] = True
                matched_cards[card_index] = True
                player_scores[player_id] += 1
                broadcast_message({
                    "type": "MATCH_RESULT",
                    "player_id": player_id,
                    "cards": [prev_index, card_index],
                    "score": player_scores[player_id]
                })
            else:
                # Let everyone see the mismatch for a moment
                time.sleep(2)
                # Then flip them back down
                faceup_cards[prev_index] = False
                faceup_cards[card_index] = False
                is_next_turn = True
                

            # Clean up locks and reset for the next turn
            per_card_locks[prev_index].release()
            per_card_locks[card_index].release()
            pidx = prev_index
            first_flipped_card = None

            # If every pair is matched, the game is then over
            if all(matched_cards):
                broadcast_message({"type": "GAME_OVER", "scores": player_scores})
    
    if (is_next_turn):
        cidx = card_index
        broadcast_message({"type": "HIDE_CARDS", "cards": [pidx, cidx]})
        # Move on to the next player's turn
        current_player_index = (current_player_index + 1) % len(connected_clients)
        send_turn_notification()

# -----------------------------------------------------------------------------------------------------
#  New Client Handler                
# ----------------------------------------------------------------------------------------------------

def handle_client_connection(client_conn, client_addr, player_id, expected_count):
    """
    When someone joins:
      - Say hi and tell them their player number
      - Once enough players are here, start the game
      - Listen for their flip requests until they disconnect
    """
    global is_game_started
    print(f"Player {player_id} connected from {client_addr}")
    send_message_to_client(client_conn, {"type": "WELCOME", "player_id": player_id, "max_players": expected_count})

    # If we've reached the expected player count, kick off the game
    with clients_lock:
        if len(connected_clients) == expected_count and not is_game_started:
            start_game()

    recv_buffer = ""
    try:
        while True:
            data = client_conn.recv(4096).decode()
            if not data:
                # Client closed the connection
                break
            recv_buffer += data
            while '\n' in recv_buffer:
                line, recv_buffer = recv_buffer.split('\n', 1)
                message = json.loads(line)
                if message.get('type') == 'FLIP_CARD':
                    process_flip_request(
                        player_id,
                        message.get('card_index'),
                        client_conn
                    )
    except Exception as error:
        print(f"Oops, error with player {player_id}: {error}")
    finally:
        print(f"Player {player_id} went away.")
        with clients_lock:
            # Remove them from our list
            connected_clients[:] = [c for c in connected_clients if c[2] != player_id]
        client_conn.close()

# --------------------------------------------------------------------------------------
#  Main Server Loop                  
# -----------------------------------------------------------------------------------------

def main():
    # Figure out how many players we expect
    args = parse_args()
    expected_players = args.players
    next_player_id = 1

    # Open up our listening socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen()
        print(
            f"Ready on {SERVER_HOST}:{SERVER_PORT}, "
            f"waiting for {expected_players} players..."
        )

        # Keep accepting new players
        while True:
            client_conn, client_addr = server_socket.accept()

            with clients_lock:
                if len(connected_clients) >= expected_players:
                    # Too many folks—tell them to come back later
                    send_message_to_client(
                        client_conn,
                        {"type": "ERROR", "message": "Sorry, game is full."}
                    )
                    client_conn.close()
                    continue
                # Assign them a player number and save their connection
                player_id = next_player_id
                next_player_id += 1
                connected_clients.append((client_conn, client_addr, player_id))

            # Spin up a thread just for this player
            thread = threading.Thread(
                target=handle_client_connection,
                args=(client_conn, client_addr, player_id, expected_players),
                daemon=True
            )
            thread.start()

if __name__ == '__main__':
    main()
