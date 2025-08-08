import pygame
import socket
import threading
import json

SERVER_HOST = 'localhost'
SERVER_PORT = 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_HOST, SERVER_PORT))
recv_buffer = ''
player_id = None
my_turn = False
game_started = False
game_over = False
current_player = 1                      # who's turn it is: player 1 to 4
game_full = False
player_disconnected = (False, None)     # (disconnected, player_id)
pid_list = []

state_lock = threading.Lock()

# save cards revealed and matched
revealed_identities = [None] * 16
matched_cards = [False] * 16
max_players = 4
scores = {} # {pid: score}


# listening to server messages and responses, run on a thread
def listen_to_server():
    global recv_buffer, player_id
    while True:
        try:
            data = client_socket.recv(4096).decode()
            if not data:
                break
            recv_buffer += data
            while '\n' in recv_buffer:
                line, recv_buffer = recv_buffer.split('\n', 1)
                message = json.loads(line)
                # print(f"[DEBUG] Received from server: {message}")  # Debug print here
                handle_server_message(message)
        except Exception as e:
            print("Server error:", e)
            break

# prints out messages from the server and changes variables based on player and game state
def handle_server_message(message):
    global player_id, my_turn, game_started, revealed_identities, matched_cards, scores, max_players, current_player, game_over, game_full, player_disconnected, pid_list

    msg_type = message.get("type")
    with state_lock:
        if msg_type == "WELCOME":
            player_id = message["player_id"]
            max_players = message["max_players"]
            player_index = message["player_index"]
            print(f"Welcome! You are Player {player_index}, there is a maximum of {max_players} players.")
        elif msg_type == "CARD_REVEALED":
            idx = message["card_index"]
            identity = message["identity"]
            revealed_identities[idx] = identity
            print(f"Card revealed: index={idx}, identity={identity}")
        elif msg_type == "MATCH_RESULT":
            for idx in message["cards"]:
                matched_cards[idx] = True
            print(f"Player {message['player_id']} found a match: {message['cards']}")
            print(scores)
            print(message["player_id"])
            scores[str(message["player_id"])] += 1
        elif msg_type == "HIDE_CARDS":
            for idx in message["cards"]:
                revealed_identities[idx] = None
            print(f"Hiding cards: {message['cards']}")
        elif msg_type == "GAME_START":
            game_started = True
            game_over = False
            revealed_identities = [None] * 16
            matched_cards = [False] * 16
            scores = message["scores"]
            pid_list = message["players"]
            print("Game started!")
        elif msg_type == "GAME_OVER":
            print("Game over! Scores:", message["scores"])
            game_over = True
            scores = message["scores"]
        elif msg_type == "ERROR":
            print("Error:", message["message"])
            if message["message"] == "Sorry, game is full.":
                game_full = True
        elif msg_type == "YOUR_TURN":
            if message["player_id"] == player_id:
                my_turn = True
                print("It's your turn!")
            else:
                my_turn = False
                current_player = message["current_player"]
                print(f"Player {current_player}'s turn. (player_id: {message['player_id']})")
            scores = message["scores"]
            print("Current scores:", scores)
        elif msg_type == "DISCONNECT":
            player_disconnected = True, message["player_id"]
            game_full = False
        elif msg_type == "GAME_FULL":
            game_full = True
            player_disconnected = (False, None)

pygame.init()
pygame.font.init()

#  setup screen and it's parameters
gameWidth = 1050
gameHeight = 1000
cardImgSize = 150
cardColumns = 4
cardRows = 4
padding = 10
leftMargin = (gameWidth - ((cardImgSize + padding) * cardColumns)) // 2
topMargin = (gameHeight - ((cardImgSize + padding) * cardRows)) // 2

screen = pygame.display.set_mode((gameWidth, gameHeight), pygame.RESIZABLE)

#  setup the window and it's parameters
pygame.display.set_caption('Memory Match')
gameIcon = pygame.image.load('resources/assets/icon.png')
pygame.display.set_icon(gameIcon)

#  setup background and it's parameters
bgImage = pygame.image.load('resources/assets/background.png')
bgImage = pygame.transform.scale(bgImage, (gameWidth, gameHeight))
bgImageRectangle = bgImage.get_rect()

#  setup card images same as we have on the server
cards = list(range(8)) * 2

card_image_map = {}
for identity in range(8):
    image = pygame.image.load(f'resources/images/cardArt/{identity}.png')
    image = pygame.transform.scale(image, (cardImgSize, cardImgSize))
    card_image_map[identity] = image

# Placeholder image for face-down cards
back_image = pygame.image.load('resources/images/cardArt/back.png')
back_image = pygame.transform.scale(back_image, (cardImgSize, cardImgSize))

# Create card rects for placement
cardRects = []
for i in range(len(cards)):
    rect = pygame.Rect(0, 0, cardImgSize, cardImgSize)
    rect.x = leftMargin + ((cardImgSize + padding) * (i % cardColumns))
    rect.y = topMargin + ((cardImgSize + padding) * (i // cardRows))
    cardRects.append(rect)
# Create player score text
font = pygame.font.SysFont("Comic Sans MS", 30)
score_texts = {i+1: font.render(f"Player {i + 1}: 0", True, (255, 255, 255)) for i in range(max_players)}

# top_text = font.render("Waiting for players", True, (255, 255, 255))
# prints to be deleted only for DEBUG
# print(cards)
# print(cardRects)

gameLoop = True

threading.Thread(target=listen_to_server, daemon=True).start()
play_again_rect = pygame.Rect(0, 0, 0, 0)

while gameLoop:
    #  load background image
    screen.blit(bgImage, bgImageRectangle)

    with state_lock:
        # Draw cards based on current revealed/matched state
        if game_over:
            top_text = font.render("Game Over! Here's the results!", True, (255, 255, 255))
            screen.blit(top_text, (gameWidth // 2 - top_text.get_width() // 2, 10))

            # Display leader board
            sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            leader_board = []
            for pid, score in sorted_scores:
                pid = int(pid)
                score_text = f"Player {pid_list.index(pid) + 1}: {score}"
                if pid == player_id:
                    score_text = f"Your Score: {score}"
                leader_board.append(font.render(score_text, True, (255, 255, 255)))
            for i, text in enumerate(leader_board):
                if i >= max_players:
                    break
                x = gameWidth // 2 - text.get_width() // 2
                y = 50 + i * 40
                screen.blit(text, (x, y))
            
            # Display play again option
            play_again_text = font.render("Click to play again", True, (255, 255, 255))
            if player_disconnected[0]:
                play_again_text = font.render(f"Player {pid_list.index(player_disconnected[1]) + 1} has disconnected. Waiting for new player...", True, (255, 255, 255))
            play_again_size = play_again_text.get_size()
            play_again_bg = pygame.Surface((play_again_size[0] + 20, play_again_size[1] + 20))
            play_again_bg.fill((0, 0, 0))
            play_again_bg.set_alpha(150)
            play_again_rect = play_again_bg.get_rect(center=(gameWidth // 2, gameHeight // 2 + 100))
            screen.blit(play_again_bg, play_again_rect)
            
            screen.blit(play_again_text, (play_again_rect.x + 10, play_again_rect.y + 10))
        else:
            for i, rect in enumerate(cardRects):
                if matched_cards[i] or revealed_identities[i] is not None:
                    identity = revealed_identities[i] if revealed_identities[i] is not None else 0
                    screen.blit(card_image_map[identity], rect)
                else:
                    screen.blit(back_image, rect)
            # update player scores
            for pid, score in scores.items():
                pid = int(pid)
                player_idx = pid_list.index(pid) + 1
                score_text = f"Player {player_idx}: {score}"
                # print(f"Pid: {pid}, Player ID: {player_id}, Score: {score}")
                if pid == player_id:
                    score_text = f"Your Score: {score}"
                #print(f"Updating score for Player {i}: {score_text}")
                score_texts[player_idx] = font.render(score_text, True, (255, 255, 255))
            # Draw player scores
            for i, text in score_texts.items():
                if i > max_players:
                    break
                screen.blit(text, (10, 10 + int(i) * 40))
            # Draw top text
            if not game_started and not game_full:
                top_text = font.render("Waiting for players", True, (255, 255, 255))
            elif game_full and player_id is None:
                top_text = font.render("Game is full. Please retry later.", True, (255, 255, 255))
            elif player_disconnected[0] and not game_full:
                top_text = font.render(f"Player {pid_list.index(player_disconnected[1]) + 1} has disconnected. Waiting for new player...", True, (255, 255, 255))
            else:
                if my_turn:
                    top_text = font.render("Your turn! Click to flip a card.", True, (255, 255, 255))
                else:
                    top_text = font.render(f"Player {current_player}'s turn: Waiting for your turn...", True, (255, 255, 255))
    screen.blit(top_text, (gameWidth // 2 - top_text.get_width() // 2, 10))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameLoop = False
        #  screen resizing
        elif event.type == pygame.VIDEORESIZE:
            gameWidth = event.w
            gameHeight = event.h
            screen = pygame.display.set_mode((gameWidth, gameHeight), pygame.RESIZABLE)
            bgImage = pygame.transform.scale(bgImage, (gameWidth, gameHeight))
            leftMargin = (gameWidth - ((cardImgSize + padding) * cardColumns)) // 2
            topMargin = (gameHeight - ((cardImgSize + padding) * cardRows)) // 2
            for i in range(len(cardRects)):
                cardRects[i].x = leftMargin + ((cardImgSize + padding) * (i % cardColumns))
                cardRects[i].y = topMargin + ((cardImgSize + padding) * (i // cardRows))
        #  on click
        elif event.type == pygame.MOUSEBUTTONDOWN:
            with state_lock:
                if not game_started:
                    print("Game not started yet. Click ignored.")
                    continue
                if not my_turn and not game_over:
                    print("Not your turn, can't flip.")
                    continue
                if game_over:
                    if play_again_rect.collidepoint(event.pos):
                        message = {"type": "PLAY_AGAIN"}
                        client_socket.sendall((json.dumps(message) + '\n').encode())
                    continue
            # sending flip card messages to the server
            mouse_x, mouse_y = pygame.mouse.get_pos()
            for i, rect in enumerate(cardRects):
                if rect.collidepoint(mouse_x, mouse_y):
                    if player_id is not None and not player_disconnected[0]:
                        message = {"type": "FLIP_CARD", "card_index": i}
                        client_socket.sendall((json.dumps(message) + '\n').encode())
                    break

    pygame.display.update()

client_socket.close()
pygame.quit()
