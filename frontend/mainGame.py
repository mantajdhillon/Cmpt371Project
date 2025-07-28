import pygame
import os
import random

pygame.init()


#  setup screen and it's parameters
SCREEN_WIDTH = 850
SCREEN_HEIGHT = 850
CARD_SIZE = 128
GAME_ROWS = 4
GAME_COLUMNS = 4
PADDING = 10

LEFT_MARGIN = (SCREEN_WIDTH - ((CARD_SIZE + PADDING) * GAME_COLUMNS)) // 2
RIGHT_MARGIN = LEFT_MARGIN
TOP_MARGIN = (SCREEN_HEIGHT - ((CARD_SIZE + PADDING) * GAME_ROWS)) // 2 
BOTTOM_MARGIN = TOP_MARGIN

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

#  setup the window and it's parameters
pygame.display.set_caption('<INSERT GAME NAME, mainGame.py>')
gameIcon = pygame.image.load('assets/icon.png')
pygame.display.set_icon(gameIcon)

#  setup background and it's parameters
bgImage = pygame.image.load('assets/background.png')
bgImage = pygame.transform.scale(bgImage, (SCREEN_WIDTH, SCREEN_HEIGHT))
bgImageRectangle = bgImage.get_rect()

# List of memeory pics
memoryCards = []

for item in os.listdir('images/'):
    memoryCards.append(item.split('.')[0])

memoryCards.extend(memoryCards.copy())

random.shuffle(memoryCards)

# load in pics
pics = []
picsRect = []
hiddenImages = []

for item in memoryCards:
    pic = pygame.image.load(f'images/{item}.jpg')
    pic = pygame.transform.scale(pic, (CARD_SIZE,CARD_SIZE))
    pics.append(pic)
    picRect = pic.get_rect()
    picsRect.append(picRect)

for i in range(len(picsRect)):
    col = i % GAME_COLUMNS
    row = i // GAME_COLUMNS
    picsRect[i][0] = LEFT_MARGIN + ((CARD_SIZE + PADDING) * col)
    picsRect[i][1] = TOP_MARGIN + ((CARD_SIZE + PADDING) * row)
    hiddenImages.append(False)


print(pics)
print(picsRect)
print(hiddenImages)

gameLoop = True

while gameLoop:
    # load in backgrounf
    screen.blit(bgImage, bgImageRectangle)

    for i in range(len(memoryCards)):
        screen.blit(pics[i], picsRect[i])

    #  input for events in game
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameLoop = False

    pygame.display.update()

pygame.quit()
