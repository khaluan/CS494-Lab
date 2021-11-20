from pygame import USEREVENT
# Color constant
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
BACKGROUND = WHITE

# Custom pygame event code
SERVER_RESPONSE = USEREVENT + 1

# Regex
NAME_REGEX = '^[a-zA-Z0-9_]{0,10}$'
CHOICE_REGEX = '^[A-D]{0,1}$'

# Asset path
LOGO_PATH = 'Asset/Logo.png'
PLAYER_PATH = 'Asset/Player.png'