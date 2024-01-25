"""
The main module that houses the Clue Solver 'Engine', which holds all deductive and Turn processing logic.
"""
import os
import atexit
import dill
import time

from defs import (ClueCardSet, Turn, Player, CATEGORIES, NUM_CARDS, ALL_CARDS, NOBODY,
                  COLORS, COLORMAP, CARD_TO_CATEGORY, SORT_ORDER)

class Engine(object):
    """
    The Engine is the Central Nervous System of this Clue Solver tool.
    It keeps track of all Turns in the game with self.turn_sequence
    It processes Turn information and performs deductive logic after each Turn to
        determine for YOU, the Player & user of this tool, what cards the other Players have
    """
    # accusation is the set of cards KNOWN to solve the murder and wins the game
    accusation = ClueCardSet()

    def __init__(self, num_players, my_player_number, my_hand):
        """

        :param num_players:
        :param my_player_number:
        :param my_hand:
        """
        # Initialize turn list with blank turn
        self.turn_sequence: list[Turn] = [Turn(number=0, is_pass=True)]
        self.my_hand: list[str] = my_hand
        self.accusation_dict = {}

        # Initialize player list with No-Op player
        self._player_list: list[Player] = [NOBODY]
        self.all_players: list[Player] = []  # All active players in game
        self.other_players: list[Player] = []  # All players besides me
        self.num_players: int = num_players
        self.my_player_number = my_player_number
        self.my_player: Player | None = None

        self.setup_players()

    def setup_players(self):
        """
        Generate Player instances for the game, including self.my_player (YOU, the user)

        Determine how many cards each Player ought to have been dealt,
            since not all Players may get the same number of cards
        """
        num_active_cards = NUM_CARDS - 3
        # Not all players may get the same number of cards
        min_cards_per_player = num_active_cards // self.num_players
        # leftover_cards are distributed to the first Players in game rotation
        leftover_cards = num_active_cards % self.num_players
        for i in range(1, self.num_players + 1):
            is_me = (i == self.my_player_number)
            hand_size = min_cards_per_player + (1 if i <= leftover_cards else 0)
            new_player = Player(number=i, size_hand=hand_size, is_me=is_me, cards=self.my_hand)
            if is_me:
                self.my_player = new_player
            self._player_list.append(new_player)

        # Ignore the No-Op Player 0 for self.all_players
        self.all_players = self._player_list[1:]
        self.other_players = [player for player in self.all_players if not player.is_me]

    def get_player(self, player_num):
        """Return the Player object"""
        return self._player_list[player_num]

    def run(self):
        """
        The entire game happens here. The general order of operations is:
            1. The Engine logs what it knows so far to the user
            2. The user informs the Engine what transpired during the Turn
            3. The Engine processes all Turns, past and present, with its ever-growing
                accumulation of knowledge to produce more knowledge about what everyone is holding
            4. If it is the user's turn and the Engine has deduced the solution, it will tell the
                user to make their Accusation
        """
        while True:
            turn_number = len(self.turn_sequence)
            suggester_num = (turn_number % self.num_players) or self.num_players
            suggester = self.get_player(suggester_num)

            # Log game details, including Players' hands, to the console
            print_separator_line()
            self.print_player_hands(turn_number)

            # Log to the user past Turn info, so the user can make an informed suggestion on their turn
            self.offer_turn_intel()

            # Enter Turn information to the Engine
            if self.take_turn(turn_number, suggester):
                """
                The Engine does all of its logic to determine:
                    1. Who has what
                    2. What was revealed during each Turn
                """
                self.process_turns_for_info()

            if suggester.is_me and self.ready_to_accuse():
                print("****** You are ready to accuse!")
                self.offer_turn_intel(ready=True)
                break

    def take_turn(self, turn_number, suggester: Player):
        """
        Store all information about the Turn in the Engine

        The input from the user to the Engine on each Turn is one of the following
            > 'pass'
            > 'update'
            > (card_1,card_2,card_3,revealing_player_number)
                e.g. > 'rope,green,hall,2'
                Meaning, Player 2 showed a card to the Suggesting Player, who guessed it was
                Mr. Green in the Hall with the Rope
                If no player revealed a card to the Suggester, then 0 should be submitted
                as the revealer_player_number

        :return bool: True if turn was taken, False if suggester Player passed
        """
        print_color(COLORS.YELLOW, f"\nTurn # {turn_number}")
        print(f"Player {suggester.number} takes turn")

        parameters = handle_input(
            "-- Enter Turn Details\n   (Suggestion + Revealing Player Number, or 'PASS', or 'UPDATE'): "
        )

        if parameters.upper().strip() == "PASS":
            # User indicates that the Suggester decline to make a suggestion
            self.turn_sequence.append(Turn(number=turn_number, is_pass=True))
            return False
        elif parameters.upper().strip() == 'UPDATE':
            """
            Here, the user indicates that they wish to manually update the Engine's accumulated knowledge,
                before proceeding with entering the Turn details
            """
            self.user_updates_hands(turn_number)
            # Recursive call here because we want to get the Turn details after the user update
            return self.take_turn(turn_number, suggester)

        # Parse the Turn details
        suggestion_set, revealer_num = parameters.rsplit(sep=',', maxsplit=1)
        revealer_num = int(revealer_num)
        if revealer_num < 1:
            revealer_num = 0  # Player == NOBODY
        suggestion_set = suggestion_set.split(',')
        revealer = self.get_player(revealer_num)
        turn = Turn(
            number=turn_number,
            suggestion=suggestion_set,
            suggester=suggester,
            revealer=revealer,
        )

        if turn.suggester.is_me and turn.revealer is not NOBODY:
            # If user is the suggester Player and a card was revealed, store that card in turn.revealed_card
            turn.revealed_card = handle_input(
                f"   Player {turn.suggester.number} is You! What card did you see? "
            )

        # Perform post-turn deductions that only need to happen once, immediately after a turn
        self.one_time_turn_deductions(turn)
        self.turn_sequence.append(turn)

        return True

    def one_time_turn_deductions(self, turn: Turn):
        """Perform post-turn deductions that only need to happen once, immediately after a turn"""
        if turn.is_pass:
            # There's nothing to process about a passed Turn
            return

        """
        We know that Players who abstained from revealing a card to the suggester must not
          have any cards in the suggestion set
        """
        self.remove_set_from_possibles(
            players=self.get_non_revealing_responders(turn), cards=turn.suggestion
        )

        """
        A 'totally processed' Turn is one in which the revealer's known HAND intersects
          with the Turn's suggestion. This happens also when there is no revealer, or the revealer is the user.
          There's no new information to gain about the revealer's HAND from this Turn, 
          once the turn is totally processed
        """
        if turn.revealer is NOBODY:
            turn.totally_processed = True
            turn.possible_reveals = set()
        elif turn.revealer.is_me:
            turn.totally_processed = True
            turn.possible_reveals &= self.my_player.hand
        elif turn.suggester.is_me:
            # Revealed card will be removed from other Players' POSSIBLES during process_turn()
            turn.possible_reveals = {turn.revealed_card}

    def user_updates_hands(self, turn_number):
        """
        User identifies whether they **think** a player HAS or LACKS a certain card
            This updates that Player's HAND and POSSIBLES, and proceeds with the Engine's logical deductions.

        It is entirely possible for an update provided by the user to be incorrect, which
            will effectively render this Engine unreliable for the remainder of the game. Use with caution.
        """
        prompt = "-- What's the information update you'd like to apply? Enter in the format '<player_num>,[has|lacks],<card>': "
        parameters = handle_input(prompt)

        # Parse the input
        player_num, action, card = parameters.split(',')
        player = self.get_player(int(player_num))

        if action == 'has':
            # Move a card from the Player's POSSIBLES to its HAND
            msg = f" > > Adding '{color_cards(card)}' to Player {player_num}'s HAND "
            player.hand |= {card}
            # Remove the card from all other Players' POSSIBLES
            self.remove_set_from_possibles(self.all_players, {card})

        else:  # action == 'lacks'
            # Remove the card from the Player's POSSIBLES
            msg = f"Removing '{color_cards(card)}' from Player {player_num}'s POSSIBLES "
            player.possibles -= {card}

        msg += 'and re-running deductions'
        print(msg)
        print_separator_line()

        self.process_turns_for_info()
        self.print_player_hands(turn_number)
        self.offer_turn_intel()

    def get_non_revealing_responders(self, turn: Turn):
        """
        Return the sequence of players ("responders") in a turn that "passed" on a suggestion
            (did not reveal a clue card), up until but NOT including the revealer
        :param Turn turn:
        :return list[Player]:
        """
        sug_num = turn.suggester.number
        rev_num = turn.revealer.number

        if rev_num < 1:  # No revealed card... return everyone BUT the suggester
            return self._player_list[sug_num + 1:] + self._player_list[1:sug_num]
        elif sug_num < rev_num:
            return self._player_list[sug_num + 1:rev_num]
        else:
            return self._player_list[sug_num + 1:] + self._player_list[1:rev_num]

    def deduce_murder_cards(self):
        """
        Try to deduce a subset of the Murder Cards in this game (i.e. the accusation)
            by examining all Players' HANDS and POSSIBLES

        :return bool: Whether we deduced more of the Murder
        """
        old_accusation = self.accusation.copy()

        # Establish all cards that we know are held, as well as all cards still potentially held
        all_hands = set()
        all_hands_and_possibles = set()
        for player in self.all_players:
            all_hands.update(player.hand)
            all_hands_and_possibles.update(player.hand | player.possibles)

        for category in CATEGORIES:
            # If all but one card from a category is in players' HANDS, the outcast must be a Murder Clue
            #  e.g. if we know who has Green, Plum, White, Scarlet, and Peacock, then Mustard must be the SUSPECT
            cat_cards_not_in_hands = set(category.__members__.keys()) - all_hands
            if len(cat_cards_not_in_hands) == 1:
                self.accusation |= cat_cards_not_in_hands
            elif len(cat_cards_not_in_hands) < 1:
                raise ValueError(
                    f"All cards from the same category are considered in play, which is impossible!: {category.__name__}"
                )

            # If a card is not in any HANDS or POSSIBLES, it must be a Murder Clue
            inactive_cat_cards = set(category.__members__.keys()) - all_hands_and_possibles
            if len(inactive_cat_cards) == 1:
                self.accusation |= inactive_cat_cards
            elif len(inactive_cat_cards) > 1:
                raise ValueError(
                    f"Multiple cards from the same category are considered out of play!: {category.__name__}:{inactive_cat_cards}"
                )

        if len(self.accusation) > len(old_accusation):
            # If we gained a new murder clue, make sure it's removed from player POSSIBLES
            self.remove_set_from_possibles(
                players=self.other_players, cards=self.accusation
            )

            # A Clue can not be a revealed card in a Turn, so update all relevant Turns
            for turn in self.turn_sequence:
                if not turn.totally_processed:
                    turn.possible_reveals -= self.accusation
            return True

        return False

    def offer_turn_intel(self, ready=False):
        """
        Log to the console the complete Turn history, including every Turn's suggestion, the cards that were
            possibly revealed, and the card that definitely was revealed (according to our deductions)

        :param bool ready: Whether to skip the Turn history and get right to the murder cards
        :return:
        """
        if not ready:
            print_color(COLORS.GREEN, "\nPast Turns:")
            for turn in self.turn_sequence:
                if turn.is_pass or turn.suggester.is_me:
                    continue
                if turn.totally_processed and len(turn.possible_reveals) > 1:
                    # Possibly trim turn.possible_reveals for turns that are already .totally_processed
                    turn.possible_reveals &= (turn.revealer.hand | turn.revealer.possibles)
                print(f"   Turn {turn.number}: Suggester:{turn.suggester.number} Revealer:{turn.revealer.number} Suggestion:{color_cards(turn.suggestion)} Possible Reveals:{color_cards(turn.possible_reveals)}")
        if self.accusation:
            # If at least one of the Murder cards has been deduced, log this
            print(f"\n** Murder Cards: {color_cards(self.accusation)}")

    def ready_to_accuse(self):
        """
        Return True if self.accusation is a complete set of cards, meaning
            it contains one card per category (Suspect, Weapon, Room)
        """

        # TODO validate that self.accusation has one card per category, in addition to checking overall set length
        return len(self.accusation) == 3

    def process_turns_for_info(self):
        """
        Perform deductions of who-has-what based on the information available from the game's Turn sequence.
        If a pass through the turn sequence yielded new info (narrowing down other players' hands),
            loop through the turn sequence again.
        """
        got_info = True
        while got_info:
            got_info = False
            # Traverse turns reverse-sequentially
            for turn in self.turn_sequence[::-1]:
                # Don't need to process Turns that are 'solved'
                if not turn.totally_processed:
                    got_info |= self.process_turn(turn)

            # After running through all past Turns, see if we've determined part of the solution
            got_info |= self.deduce_murder_cards()
            # Further deductive reasoning based on what is known about Player hands
            got_info |= self.check_players_hand_size()

    def process_turn(self, turn: Turn):
        """
        If we determined the card revealed during a Turn,
            remove that card from all Players' POSSIBLES

        :param Turn turn:
        :return bool:       Whether information was gained during this method call
        """
        if self.process_revealed_turn(turn):
            # We added to our knowledge of a player's HAND
            self.remove_set_from_possibles(
                players=self.other_players, cards={turn.revealed_card}
            )
            return True
        return False

    @staticmethod
    def process_revealed_turn(turn: Turn):
        """
        Narrow down the possibilities for the card revealed to the Suggester during this Turn.
          We know that the revealed card CAN'T be in any other player's HAND,
          And MUST be in the revealer's POSSIBLES.

        :return bool: Whether this deductive step revealed new information about players' hands or Turns
        """
        if turn.possible_reveals & turn.revealer.hand:  # Intersection
            # At least one of the cards in the suggestion are already known to be in the revealer's hand.
            #   We can't get any more information from this Turn
            turn.totally_processed = True
            return False

        # The revealed card must be in the revealer's POSSIBLES
        turn.possible_reveals &= turn.revealer.possibles
        if len(turn.possible_reveals) == 1:
            # We've zeroed in on the revealed card for this turn
            turn.revealed_card = list(turn.possible_reveals)[0]
            turn.revealer.hand |= {turn.revealed_card}
            turn.totally_processed = True
            return True
        elif len(turn.possible_reveals) < 1:
            print("ERROR: len(turn.possible_reveals) < 1")
            print(f"Turn: {vars(turn)}")
            print("suggester", vars(turn.suggester))
            print("responder", vars(turn.revealer))
            raise ValueError('turn.possible_reveals has length 0 after reductions')

        # We got information from this turn if we narrowed down the possible_reveals
        return False

    def check_players_hand_size(self):
        """
        If a Player's HAND and POSSIBLES combined is equal to hand_size, make them all part of their HAND
        If a Player has HAND size equal to .hand_size, wipe out their POSSIBLES
            since we know all their cards

        :return bool: Whether a player's entire hand was determined
        """
        got_info = False
        # Only want to consider OTHER players with unsolved HANDS
        for player in self.other_players:
            if len(player.possibles) == 0:
                continue
            if len(player.hand) == player.hand_size:
                # Reduce player.possibles is a gain in information
                player.possibles = set()
                got_info = True
            elif len(player.hand) + len(player.possibles) == player.hand_size:
                player.hand.update(player.possibles)
                # No other Player can possibly be holding Player.hand
                self.remove_set_from_possibles(self.other_players, player.hand)
                got_info = True
        return got_info

    @staticmethod
    def remove_set_from_possibles(players: list[Player], cards: set[str]):
        """
        Remove a set of cards from the POSSIBLES of the given Players.

        :param players:
        :param cards:
        """
        for player in players:
            player.possibles -= cards  # Removal from set

    def print_player_hands(self, turn_number):
        """
        Log to the console the known HAND and the POSSIBLE cards held by each Player

        :param turn_number:
        :return:
        """
        print(f"\t\t\t{COLORS.WHITE}CARD DISTRIBUTION{COLORS.RESET}")
        for player in self.all_players:
            if player.is_me:
                print_color(COLORS.CYAN, f"++ Player {player.number} (YOU!)")
                print(f"      {COLORS.CYAN}Hand:{COLORS.RESET}      {color_cards(player.hand)}")
            else:
                # For non-user Players, indicate the size of the Player's HAND, even if not all cards in the HAND are known
                print(
                    f"++ {COLORS.WHITE}Player {player.number}{COLORS.RESET} [{len(player.hand)}/{player.hand_size}]"
                )
                print(f"      Hand:      {color_cards(player.hand)}")
            if len(player.possibles):
                self.print_cards("      Possibles: ", player.possibles_dict)

    @staticmethod
    def print_cards(prefix: str, cards: dict):
        """
        Print a collection of cards, grouped by category (SUSPECT, WEAPON, ROOM)

        :param str prefix:
        :param dict cards: the dict representation of a ClueCardSet
        """
        s = prefix
        indent = f"\n{' ' * len(prefix)}"
        ctr = 0
        for cat in CATEGORIES:
            cat_cards = cards.get(cat.__name__, set())
            if cat_cards:
                s += f"{indent if ctr else ''}{cat.__name__}: {color_cards(cat_cards)}"
                ctr += 1
        print(s)


def print_separator_line():
    print(f"\n----------------------------------------------------------")


def print_color(color, msg_str):
    """Colorize the entire msg_str"""
    print(color + msg_str + COLORS.RESET)


def _colorize(card):
    """
    Find the appropriate ANSI color code for the card based on category,
        and wrap card in color code characters

    :param str card:
    :return str:
    """
    color_code = COLORMAP[CARD_TO_CATEGORY[card.lower()]]
    return color_code + card + COLORS.RESET


def color_cards(cards):
    """
    Wrap input item(s) in ANSI color codes for colorful output to the console
        The color applied to each item depends on what Clue Category it belongs to (Suspect, Room, Weapon)
    :param str|iter cards:      String or Iterable of Strings
    :return:                    Input wrapped in ANSI color codes (with RESET terminator included)
    """
    if isinstance(cards, str):
        return _colorize(cards)
    elif hasattr(cards, '__iter__'):
        sorted_cards = sorted(cards, key=lambda x: (SORT_ORDER[CARD_TO_CATEGORY[x]], x))
        return '[' + ', '.join([_colorize(card) for card in sorted_cards]) + ']'
    else:
        raise ValueError("Input to color_card() neither a string nor an iterable!")


PICKLE_STATE = 'engine_state.pkl'
PICKLE_GAME = 'game_play.pkl'
ALLOWABLE_INPUTS = ['pass', 'update', 'has', 'lacks']


def handle_input(prompt: str = 'Default Prompt:', splitter: str = ','):
    """
    Received input from user and validated.
    Input should be a comma-delimited, alphanumeric string.
    For all non-numeric entries, check against list of valid game cards (e.g. 'white')
        and other allowed phrases (ALLOWABLE_INPUTS) (e.g. 'PASS')

    :param prompt:      The prompt to display to the user
    :param splitter:    The character to split input on
    :return:            The validated input from user, lower-cased
    """
    while True:
        valid_input = True
        user_input = input(prompt).lower()
        for item in user_input.split(splitter):
            if item.isalpha():
                if item not in ALL_CARDS and item not in ALLOWABLE_INPUTS:
                    valid_input = False
                    print_color(
                        COLORS.INVERSE,
                        f" ! ! Unable to recognize input '{item}'. Please try again...",
                    )
                    break
        if valid_input:
            break
    return user_input


def main():
    """
    Launch the Engine, which operates from the user's POV playing the game
    This function also configures the interpreter to dump the game's state upon closure,
        so that if a particular game state caused the Engine to crash, you can return to that
        game after examining and resolving the bug.
    """
    os.system('cls' if os.name == 'nt' else 'clear')
    print_color(COLORS.CYAN, "\n\t\tWelcome to Clue Solver!")
    print_color(COLORS.WHITE, "\tA Deduction Engine for the Board Game 'Clue'\n")

    print(
        f"**{COLORS.RED}IMPORTANT{COLORS.RESET}**: Deal game cards to players according to gameplay rotation.\n"
        f"  e.g. Player 1 gets the first card dealt, then Player 2...\n"
        f"  This ensures that any extra cards are dealt to the first Players\n"
    )

    time.sleep(0.5)

    num_players = int(handle_input("Enter Number of Players: "))
    my_player_number = int(handle_input("\nEnter Your Player Number (Gameplay rotation position): "))
    my_hand = handle_input(f"\nEnter Your Hand, comma-separated (e.g. '{COLORS.GREEN}knife,hall,pipe,...{COLORS.RESET}'): ").split(',')
    eng = Engine(num_players=num_players, my_player_number=my_player_number, my_hand=my_hand)

    """
    After a game terminates, either through natural completion or from a crash,
    pickle and dump the game state locally for debugging purposes.
    Use the module rerun.py to "pick up where you left off" once you (think you) have fixed the bug!
    """
    def dump_engine_state(*args):
        print(f"Dumping Pickled Engine State to {PICKLE_STATE}")
        with open(PICKLE_STATE, "wb") as f:
            dill.dump(eng, f)

    def dump_gameplay(*args):
        gameplay_info = [
            eng.num_players,
            eng.my_player_number,
            eng.my_hand,
            eng.turn_sequence,
        ]
        print(f'Dumping Gameplay Info to {PICKLE_GAME}')
        with open(PICKLE_GAME, 'wb') as f:
            dill.dump(gameplay_info, f)

    atexit.register(dump_engine_state)
    atexit.register(dump_gameplay)

    # Start the game!
    os.system('cls' if os.name == 'nt' else 'clear')
    eng.run()


if __name__ == '__main__':
    main()
