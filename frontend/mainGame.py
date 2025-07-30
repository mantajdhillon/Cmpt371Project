import pygame
import os
import random
import socket
import threading
import json

SERVER_HOST = 'localhost'  # or IP address of the backend server
SERVER_PORT = 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((SERVER_HOST, SERVER_PORT))
recv_buffer = ''
player_id = None  # Will be set after receiving "WELCOME"
my_turn = False
game_started = False

state_lock = threading.Lock()

revealed_identities = [None] * 16  # Shows revealed identities, or None
matched_cards = [False] * 16       # True if card is matched

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
                print(f"[DEBUG] Received from server: {message}")  # Debug print here
                handle_server_message(message)
        except Exception as e:
            print("Server error:", e)
            break

def handle_server_message(message):
    global player_id, my_turn, game_started, revealed_identities, matched_cards

    msg_type = message.get("type")
    with state_lock:
        if msg_type == "WELCOME":
            player_id = message["player_id"]
            print(f"Welcome! You are Player {player_id}")
        elif msg_type == "CARD_REVEALED":
            idx = message["card_index"]
            identity = message["identity"]
            revealed_identities[idx] = identity
            print(f"Card revealed: index={idx}, identity={identity}")
        elif msg_type == "MATCH_RESULT":
            for idx in message["cards"]:
                matched_cards[idx] = True
            print(f"Player {message['player_id']} found a match: {message['cards']}")
        elif msg_type == "HIDE_CARDS":
            for idx in message["cards"]:
                revealed_identities[idx] = None
            print(f"Hiding cards: {message['cards']}")
        elif msg_type == "GAME_START":
            game_started = True
            print("Game started!")
        elif msg_type == "GAME_OVER":
            print("Game over! Scores:", message["scores"])
        elif msg_type == "ERROR":
            print("Error:", message["message"])
        elif msg_type == "YOUR_TURN":
            if message["player_id"] == player_id:
                my_turn = True
                print("It's your turn!")
            else:
                my_turn = False
                print(f"Player {message['player_id']}'s turn.")

pygame.init()


#  setup screen and it's parameters
gameWidth = 1050
gameHeight = 800
cardImgSize = 150
cardColumns = 4
cardRows = 4
padding = 10 # space between cards
leftRightMargin = (gameWidth - ((cardImgSize + padding) * cardColumns)) // 2
topBotMargin = (gameHeight - ((cardImgSize + padding) * cardRows)) // 2

screen = pygame.display.set_mode((gameWidth, gameHeight), pygame.RESIZABLE)

#  setup the window and it's parameters
pygame.display.set_caption('<INSERT GAME NAME, mainGame.py>')
gameIcon = pygame.image.load('assets/icon.png')
pygame.display.set_icon(gameIcon)

#  setup background and it's parameters
bgImage = pygame.image.load('assets/background.png')
bgImage = pygame.transform.scale(bgImage, (gameWidth, gameHeight))
bgImageRectangle = bgImage.get_rect()

#  setup card images
cards = list(range(8)) * 2  # same as server

card_image_map = {}
for identity in range(8):
    image = pygame.image.load(f'images/cardArt/{identity}.png')
    image = pygame.transform.scale(image, (cardImgSize, cardImgSize))
    card_image_map[identity] = image

# Placeholder image for face-down cards
back_image = pygame.image.load('images/cardArt/back.png')
back_image = pygame.transform.scale(back_image, (cardImgSize, cardImgSize))

# Create card rects for placement
cardRects = []
for i in range(len(cards)):
    rect = pygame.Rect(0, 0, cardImgSize, cardImgSize)
    rect.x = leftRightMargin + ((cardImgSize + padding) * (i % cardColumns))
    rect.y = topBotMargin + ((cardImgSize + padding) * (i // cardRows))
    cardRects.append(rect)

print(cards)
print(cardRects)

gameLoop = True

threading.Thread(target=listen_to_server, daemon=True).start()


while gameLoop:
    #  load background image
    screen.blit(bgImage, bgImageRectangle)

    with state_lock:
        # Draw cards based on current revealed/matched state
        for i, rect in enumerate(cardRects):
            if matched_cards[i] or revealed_identities[i] is not None:
                identity = revealed_identities[i] if revealed_identities[i] is not None else 0
                screen.blit(card_image_map[identity], rect)
            else:
                screen.blit(back_image, rect)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameLoop = False
        elif event.type == pygame.VIDEORESIZE:
            gameWidth = event.w
            gameHeight = event.h
            screen = pygame.display.set_mode((gameWidth, gameHeight), pygame.RESIZABLE)
            bgImage = pygame.transform.scale(bgImage, (gameWidth, gameHeight))
            leftRightMargin = (gameWidth - ((cardImgSize + padding) * cardColumns)) // 2
            topBotMargin = (gameHeight - ((cardImgSize + padding) * cardRows)) // 2
            for i in range(len(cardRects)):
                cardRects[i].x = leftRightMargin + ((cardImgSize + padding) * (i % cardColumns))
                cardRects[i].y = topBotMargin + ((cardImgSize + padding) * (i // cardRows))
        elif event.type == pygame.MOUSEBUTTONDOWN:
            with state_lock:
                if not game_started:
                    print("Game not started yet. Click ignored.")
                    continue
                if not my_turn:
                    print("Not your turn, can't flip.")
                    continue

            mouse_x, mouse_y = pygame.mouse.get_pos()
            for i, rect in enumerate(cardRects):
                if rect.collidepoint(mouse_x, mouse_y):
                    if player_id is not None:
                        message = {"type": "FLIP_CARD", "card_index": i}
                        client_socket.sendall((json.dumps(message) + '\n').encode())
                    break

    pygame.display.update()

client_socket.close()
pygame.quit()
