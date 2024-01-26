"""
This module holds the constant values and class definitionsthat used by the solver Engine
"""
import enum

"""
These variables represent the sets of cards in the Clue deck.
You may alter these lists if your version of Clue has different names,
  e.g. the Online version released by Hasbro has a Ms. Orchid instead of Mrs. White,
  in which case you'd replace 'white' for 'orchid' in the SUSPECTS list
"""
SUSPECT = enum.Enum('Suspect', ['white', 'plum', 'peacock', 'scarlet', 'mustard', 'green'])
WEAPON = enum.Enum('Weapon', ['rope', 'pipe', 'wrench', 'candlestick', 'knife', 'revolver'])
ROOM = enum.Enum('Room', ['billiard', 'lounge', 'conservatory', 'kitchen', 'hall',
                          'dining', 'study', 'library', 'ballroom'])

CATEGORIES = [SUSPECT, WEAPON, ROOM]
ALL_CARDS = {value for category in CATEGORIES for value in category.__members__}
NUM_CARDS = len(ALL_CARDS)
CARD_TO_CATEGORY = {m: c.__name__ for c in CATEGORIES for m in c.__members__}
SORT_ORDER = {c.__name__: i for i, c in enumerate(CATEGORIES)}

# COLORS objects used to color the output in the terminal
class COLORS:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    INVERSE = "\033[7m"
    RESET = "\033[0m"

# It's pretty when each of the card categories is a different color.
# It also helps with visual organization when the tool presents its deductions to the user
COLORMAP = dict(Suspect=COLORS.RED, Weapon=COLORS.YELLOW, Room=COLORS.BLUE)


class ClueCardSet(object):
    """
    ClueCardSet is some code magic that allows collection of Clue game cards to be
    stored as a dict of lists (keeping the cards separated by category),
    but represented as an unordered set

    e.g. If ('plum', 'knife', 'hall', 'rope') were a set of cards, behind the scenes
    it would be treated like {'Suspect': ['plum'], 'Room':['hall'], 'Weapon':['knife', 'rope']}

    I did things this way both as a challenge to myself, and because it made certain pieces of logic more elegant
    (and hopefully made no pieces of logic less elegant!)

    Each ClueCardSet object is linked to the class object that created it as a variable.
    Thus, all the dunder's you see here.

    When interacting with a CCS as a set, do not use .update() as this will not function properly.
    Instead, add elements to the set with:   set = set | other_set

    # TODO implement .update() for the set representation of a ClueCardSet, though not necessary because for the time being we can just do:   set = set | other_set
    """
    def __set_name__(self, owner, name):
        """Create the alias for the dict version of the card set"""
        self.name = name + '_dict'

    def __get__(self, instance, owner):
        """Convert the dict card collection to a set"""
        cards_by_category = instance.__dict__[self.name]
        return set([c for category_cards in cards_by_category.values() for c in category_cards])

    def __set__(self, instance, cards: set[str]):
        """Convert the set card collection to a dict"""
        instance.__dict__[self.name] = {}
        for category in CATEGORIES:
            clues = set(category.__members__) & cards
            if clues:
                instance.__dict__[self.name][category.__name__] = clues


class Player(object):
    """
    Represents a Player of the Clue Board Game, from the perspective of the user of this Engine.
    It keeps track both of what a Player is KNOWN to have as well as what it POSSIBLY has,
        based on logical deductions.
    The number of cards in a Player's 'hand' (the KNOWN cards) should never exceed the number of
        cards dealt to that Player.

    Note that active Players are indexed from 1, not 0.
    """
    hand = ClueCardSet()
    possibles = ClueCardSet()

    def __init__(self, number=0, size_hand=0, is_me=False, cards=None):
        """
        When initializing a Player during a game, unless that Player is YOU,
            you should only know how many cards that Player is holding.
            But its .hand will start off as an empty set, and its .possibles will be the complete
            set of cards in the game, except for the ones that YOUR Player instance holds
        :param number:
        :param size_hand:
        :param is_me:
        :param cards:
        """
        self.hand_dict = {}
        self.possibles_dict = {}

        # is_me indicates that the Player instance is YOUR Player instance
        self.is_me = is_me
        if cards is None:
            cards = []
        self.hand_size = size_hand
        self.number = number

        if self.number == 0:
            # Non-player should have empty sets
            self.hand = set()
            self.possibles = set()
        else:
            self.hand = set(cards if is_me else [])
            self.possibles = set([] if is_me else ALL_CARDS - set(cards))


# A No-Op player, aka 'Player 0'. Created to ease the Engine's logic when a suggestion does not have a revealer
NOBODY = Player()


class Turn(object):
    """
    A Turn consists of the following information:
      1. Turn Number
      2. The Player who's Turn it is (the 'Suggester')
      3. The Suggester's suggestion, which is a set of (SUSPECT, ROOM, WEAPON)
      4. The Player who responds with a card reveal (the 'Revealer'), if any

    A Turn's .possible_reveals is the set of cards that Might have been shown to the Suggester.
    A Turn's .revealed_card is only set once the Engine determines the exact card shown to the Suggester
        by the Revealer. This deduction might not be performed until later in the game, when more
        information has been obtained from other Turn actions.
    """
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

        # Is there no more information to be deduced about this Turn?
        self.totally_processed = False

        # Did the Suggester Pass, or simply not make a suggestion this Turn?
        self.is_pass = is_pass

        if self.is_pass:
            # Consider 'passes' to be "totally processed"
            self.totally_processed = True
            self.revealer = None
            self.possible_reveals = set()
            self.suggestion = set()
