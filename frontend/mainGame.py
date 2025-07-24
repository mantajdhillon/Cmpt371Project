import pygame

pygame.init()


#  setup screen and it's parameters
gameWidth = 1050
gameHeight = 800
screen = pygame.display.set_mode((gameWidth, gameHeight))

#  setup the window and it's parameters
pygame.display.set_caption('<INSERT GAME NAME, mainGame.py>')
gameIcon = pygame.image.load('images/icon.png')
pygame.display.set_icon(gameIcon)

#  setup background and it's parameters
bgImage = pygame.image.load('images/background.png')
bgImage = pygame.transform.scale(bgImage, (gameWidth, gameHeight))
bgImageRectangle = bgImage.get_rect()





gameLoop = True

while gameLoop:
    # load in backgrounf
    screen.blit(bgImage, bgImageRectangle)

    #  input for events in game
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            gameLoop = False

    pygame.display.update()

pygame.quit()
