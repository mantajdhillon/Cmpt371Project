import pygame
import os
import random

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
gameIcon = pygame.image.load('frontend/images/icon.png')
pygame.display.set_icon(gameIcon)

#  setup background and it's parameters
bgImage = pygame.image.load('frontend/images/background.png')
bgImage = pygame.transform.scale(bgImage, (gameWidth, gameHeight))
bgImageRectangle = bgImage.get_rect()

#  setup card images
cards = []
cardImages = []
cardRects = []

for card in os.listdir('frontend/images/cardArt/'):
    cards.append(card.split('.')[0]) # removing extension
cardsCopy = cards.copy()
cards.extend(cardsCopy) # duplicating cards for pairs
cardsCopy.clear()

for card in cards:
    cardImage = pygame.image.load(f'frontend/images/cardArt/{card}.png')
    cardImage = pygame.transform.scale(cardImage, (cardImgSize, cardImgSize))
    cardRect = cardImage.get_rect()
    cardImages.append(cardImage)
    cardRects.append(cardRect)

#  modifying x and y coordinates of rectangles for card placement
for i in range(len(cardRects)):
    cardRects[i].x = leftRightMargin + ((cardImgSize + padding) * (i % cardColumns))
    cardRects[i].y = topBotMargin + ((cardImgSize + padding) * (i // cardRows))

print(cards)
print(cardImages)
print(cardRects)

gameLoop = True

while gameLoop:
    #  load background image
    screen.blit(bgImage, bgImageRectangle)

    #  load cards on screen
    for i in range(len(cards)):
        screen.blit(cardImages[i], cardRects[i])

    #  input for events in game
    for event in pygame.event.get():
        if event.type == pygame.QUIT: # close window
            gameLoop = False
        elif event.type == pygame.VIDEORESIZE: # resize window and adjust related elements
            gameWidth = event.w
            gameHeight = event.h
            screen = pygame.display.set_mode((gameWidth, gameHeight), pygame.RESIZABLE)
            bgImage = pygame.transform.scale(bgImage, (gameWidth, gameHeight))
            leftRightMargin = (gameWidth - ((cardImgSize + padding) * cardColumns)) // 2
            topBotMargin = (gameHeight - ((cardImgSize + padding) * cardRows)) // 2
            
            for i in range(len(cardRects)): # adjust card positions to new window size
                cardRects[i].x = leftRightMargin + ((cardImgSize + padding) * (i % cardColumns))
                cardRects[i].y = topBotMargin + ((cardImgSize + padding) * (i // cardRows))
    pygame.display.update()
    
pygame.quit()
