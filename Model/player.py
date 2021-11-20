class Player:
    def __init__(self, name = '', order = -1) -> None:
        self.name = name
        self.order = order
        self.skip_turn = 1

