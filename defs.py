import enum

SUSPECT = enum.Enum('Suspect', ['white', 'plum', 'peacock', 'scarlet', 'mustard', 'green'])
WEAPON = enum.Enum('Weapon', ['rope', 'pipe', 'wrench', 'candlestick', 'knife', 'revolver'])
ROOM = enum.Enum('Room', ['billiard', 'lounge', 'conservatory', 'kitchen', 'hall',
                          'dining', 'study', 'library', 'ballroom'])


CATEGORIES = [SUSPECT, WEAPON, ROOM]
ALL_CARDS = {value for category in CATEGORIES for value in category.__members__}
NUM_CARDS = len(ALL_CARDS)


class ClueCardSet:
    def __set_name__(self, owner, name):
        self.name = name + '_dict'

    def __get__(self, instance, owner):
        d = instance.__dict__[self.name]
        return set([e for vs in d.values() for e in vs])

    def __set__(self, instance, cards: set[str]):
        instance.__dict__[self.name] = {}
        for category in CATEGORIES:
            clues = set(category.__members__) & cards
            if clues:
                instance.__dict__[self.name][category.__name__] = clues


class Player(object):

    hand = ClueCardSet()
    possibles = ClueCardSet()

    def __init__(self, number=0, size_hand=0, is_me=False, cards=None):
        self.hand_dict = {}
        self.possibles_dict = {}

        self.is_me = is_me
        if cards is None:
            cards = []
        self.size_hand = size_hand
        self.number = number

        if self.number == 0:
            # Non-player should have empty sets
            self.hand = set()
            self.possibles = set()
        else:
            self.hand = set(cards if is_me else [])
            self.possibles = set([] if is_me else ALL_CARDS - set(cards))


class Turn(object):

    suggestion = ClueCardSet()
    possible_reveals = ClueCardSet()

    def __init__(self, number: int = 0, suggestion=None, suggester: Player = None, revealer: Player = None, is_pass=False):
        self.suggestion_dict = {}
        self.possible_reveals_dict = {}

        if suggestion is None:
            suggestion = set()
        self.number = number
        self.suggester: Player = suggester
        self.revealer: Player = revealer
        self.revealed_card = None
        self.suggestion: set[str] = set(suggestion)
        self.possible_reveals: set[str] = set(suggestion)
        self.is_pass = is_pass
        # Consider 'passes' to be "totally processed"
        self.totally_processed = False or self.is_pass
