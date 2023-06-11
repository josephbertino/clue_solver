import atexit
import dill

from defs import (ClueCardSet, Turn, Player, CATEGORIES, NUM_CARDS, ALL_CARDS, NOBODY)

class Engine(object):

    accusation = ClueCardSet()

    def __init__(self, num_players, my_player_number, my_hand):
        # Initialize turn list with blank turn
        self.turn_sequence: list[Turn] = [Turn(number=0, is_pass=True)]
        self.my_hand: list[str] = my_hand
        self.accusation_dict = {}

        # Initialize player list with blank player
        self._player_list: list[Player] = [NOBODY]
        self.all_players: list[Player] = []  # All active players in game
        self.other_players: list[Player] = []  # All players besides me
        self.num_players: int = num_players
        self.my_player_number = my_player_number
        self.my_player: Player | None = None

        self.setup_players()

    def get_player(self, player_num):
        return self._player_list[player_num]

    def setup_players(self):
        """Generate Player instances for game, including self.my_player, who is You, the user"""
        num_active_cards = NUM_CARDS - 3
        # Not all players may get the same number of cards
        cards_per_player = num_active_cards // self.num_players
        leftovers = num_active_cards % self.num_players
        for i in range(1, self.num_players + 1):
            is_me = i == self.my_player_number
            size_hand = cards_per_player + (1 if i <= leftovers else 0)
            new_player = Player(number=i, size_hand=size_hand, is_me=is_me, cards=self.my_hand)
            if is_me:
                self.my_player = new_player
            self._player_list.append(new_player)

        self.all_players = self._player_list[1:]
        self.other_players = [player for player in self.all_players if not player.is_me]

    def run(self):
        while True:
            turn_number = len(self.turn_sequence)
            suggester_num = (turn_number % self.num_players) or self.num_players
            suggester = self.get_player(suggester_num)

            """Log game details to output"""
            print(f"\n----------------------------------------------------------")
            self.print_turn_player_details(turn_number)

            self.offer_clue_intel()

            if self.take_turn(turn_number, suggester):
                self.process_turns_for_info()

            if suggester.is_me and self.ready_to_accuse():
                print("****** You are ready to accuse!")
                self.offer_clue_intel(ready=True)
                break

    def take_turn(self, turn_number, suggester: Player):
        """
        :return bool: True if turn was taken, False if player passed
        """
        print(f"\n-- Player {suggester.number} {'(YOU!)' if suggester == self.my_player else ''} takes turn")

        parameters = handle_input("-- Enter Turn Parameters (Suggestion Combo + Revealing Player Number, 'PASS', or 'UPDATE'): ")
        if parameters.upper().strip() == 'PASS':
            self.turn_sequence.append(Turn(number=turn_number, is_pass=True))
            return False
        elif parameters.upper().strip() == 'UPDATE':
            self.user_updates_hands(turn_number)
            return self.take_turn(turn_number, suggester)

        suggestion, revealer_num = parameters.rsplit(sep=',', maxsplit=1)
        revealer_num = int(revealer_num)
        if revealer_num < 0:
            revealer_num = 0  # Player == NOBODY
        suggestion = suggestion.split(',')
        revealer = self.get_player(revealer_num)
        turn = Turn(number=turn_number, suggestion=suggestion, suggester=suggester, revealer=revealer)

        if turn.suggester.is_me and turn.revealer is not NOBODY:
            # If I was the suggester and a card was revealed, store turn.revealed_card
            turn.revealed_card = handle_input(f"   Player {turn.suggester.number} is You! What card did you see? ")

        self.one_time_turn_deductions(turn)
        self.turn_sequence.append(turn)
        return True

    def one_time_turn_deductions(self, turn: Turn):
        """Perform post-turn deductions that only need to happen once, immediately after a turn"""
        if turn.is_pass:
            return

        # Non-revealing responders from a turn don't have any of the suggested cards. Reduce their POSSIBLES
        self.remove_set_from_possibles(players=self.get_non_revealing_responders(turn), cards=turn.suggestion)

        # A 'totally processed' turn is one in which we know that the revealer's HAND overlaps
        #   with the suggestion (which happens automatically when there is no revealer, or the revealer is Me),
        #   so there's no new information to gain about the revealer's HAND from further processing
        if turn.revealer is NOBODY:
            turn.totally_processed = True
            turn.possible_reveals = set()
        elif turn.revealer.is_me:
            turn.totally_processed = True
            turn.possible_reveals &= self.my_player.hand
        elif turn.suggester.is_me:
            # Revealed card will be removed from player POSSIBLES during process_turn() step
            turn.possible_reveals = {turn.revealed_card}

    def user_updates_hands(self, turn_number):
        """
        User identifies whether they **think** a player HAS or LACKS a certain card
            This updates that player's HAND or POSSIBLES, and proceeds with the turn's logical deductions
            It is entirely possible for an update provided by the user to be incorrect, which
            will effectively render this Engine unreliable for the remainder of the game. Use with caution.
        """
        prompt = "-- What's the information update you'd like to apply? Enter in the form 'PLAYER_NUM [HAS|LACKS] CARD': "
        parameters = handle_input(prompt, splitter=' ')
        player_num, action, card = parameters.split(' ')
        player = self.get_player(int(player_num))
        if action == 'has':
            msg = f" > > Adding '{card}' to Player {player_num}' HAND "
            player.hand |= {card}
            self.remove_set_from_possibles(self.all_players, {card})
        else:  # action == 'lacks'
            msg = f"Removing '{card}' from Player {player_num}' POSSIBLES "
            player.possibles -= {card}
        msg += 'and re-running deductions'
        print(msg)
        self.process_turns_for_info()
        self.print_turn_player_details(turn_number)
        self.offer_clue_intel()

    def get_non_revealing_responders(self, turn: Turn):
        """
        Return the sequence of players ("responders") in a turn that "passed" on a suggestion (did not have a clue card),
            up until but NOT including the clue revealer
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

    def determine_clues(self):
        old_accusation = self.accusation.copy()

        all_hands = set()
        hands_and_possibles = set()
        for player in self.all_players:
            all_hands.update(player.hand)
            hands_and_possibles.update(player.hand | player.possibles)

        for category in CATEGORIES:
            # If all but one card from a category is in players' HANDS, the outcast must be a Clue
            cat_cards_not_in_hands = set(category.__members__.keys()) - all_hands
            if len(cat_cards_not_in_hands) == 1:
                self.accusation |= cat_cards_not_in_hands
            elif len(cat_cards_not_in_hands) < 1:
                raise ValueError(f"All cards from the same category are in play, which is impossible!: {category.__name__}")

            # If a card is not in any HANDS or POSSIBLES, it must be a Clue
            inactive_cat_cards = set(category.__members__.keys()) - hands_and_possibles
            if len(inactive_cat_cards) == 1:
                self.accusation |= inactive_cat_cards
            elif len(inactive_cat_cards) > 1:
                raise ValueError(f"Multiple cards from the same category are out of play!: {category.__name__}:{inactive_cat_cards}")

        if len(self.accusation) > len(old_accusation):
            # If we gained a new clue, make sure it's removed from player POSSIBLES
            #    (We may have determined a clue because all other cards in that category were in player HANDS...
            #    in which case that card might still be lingering in a player's POSSIBLE)
            self.remove_set_from_possibles(players=self.other_players, cards=self.accusation)
            # A Clue could also not be a revealed card in a Turn
            for turn in self.turn_sequence:
                if not turn.totally_processed:
                    turn.possible_reveals -= self.accusation
            return True

        return False

    def offer_clue_intel(self, ready: bool = False):
        if not ready:
            print("\n?? Past Turns:")
            for turn in self.turn_sequence:
                if turn.is_pass or turn.suggester.is_me:
                    continue
                if turn.totally_processed and len(turn.possible_reveals) > 1:
                    # Possibly trim turn.possible_reveals for turns that are already .totally_processed
                    turn.possible_reveals &= (turn.revealer.hand | turn.revealer.possibles)
                print(f"   Turn {turn.number}: Suggester:{turn.suggester.number} Revealer:{turn.revealer.number} Suggestion:{turn.suggestion} Possible Reveals:{turn.possible_reveals}")
        print(f"\n** Known Clues: {self.accusation_dict}")

    def ready_to_accuse(self):
        """For each of the 3 CATEGORIES (Suspect, Weapon, Room), there should be only 1 member whose value is True"""
        return len(self.accusation) == 3

    def process_turns_for_info(self):
        """
        Perform deductions of who-has-what based on the information available from the self.turn_sequence.
        If a pass through the turn sequence yielded new info (narrowing down other players' hands),
            loop through the turn sequence again.
        """
        got_info = True
        while got_info:
            got_info = False
            # Traverse turns reverse-sequentially
            for turn in self.turn_sequence[::-1]:
                if not turn.totally_processed:
                    got_info |= self.process_turn(turn)
            got_info |= self.determine_clues()
            got_info |= self.check_players_hand_size()

    def process_turn(self, turn: Turn):
        if self.process_revealed_turn(turn):
            # We added to our knowledge of a player's HAND
            self.remove_set_from_possibles(players=self.other_players, cards={turn.revealed_card})
            return True
        return False

    @staticmethod
    def process_revealed_turn(turn: Turn):
        """
        Potentially shrink possible reveals for this turn's suggestion:
          We know that the revealed card CAN'T be in any other player's HAND,
          And MUST be in the revealer's POSSIBLES.
        :return: bool
        """
        if turn.possible_reveals & turn.revealer.hand:  # Intersection
            # At least one of the cards in the suggestion are already known in the responder's hand.
            #   We can't get any more information from this turn
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
        1) If a Player's HAND and POSSIBLES combined is equal to size_hand, make them all part of their HAND
        2) If a Player has HAND size equal to size_hand, wipe out their POSSIBLES
        :return: bool Whether a player's entire hand was determined
        """
        got_info = False
        for player in self.other_players:
            if len(player.possibles) == 0:
                continue
            # Only want to consider OTHER players with unsolved HANDS
            if len(player.hand) == player.size_hand:
                # Reduce player.possibles is a gain in information
                player.possibles = set()
                got_info = True
            elif len(player.hand) + len(player.possibles) == player.size_hand:
                player.hand.update(player.possibles)
                self.remove_set_from_possibles(self.other_players, player.hand)
                got_info = True
        return got_info

    @staticmethod
    def remove_set_from_possibles(players: list[Player], cards: set[str]):
        """
        Remove a set of cards from the POSSIBLES of the given Player instances
        :param players:
        :param cards:
        """
        for player in players:
            player.possibles -= cards  # Removal from set

    def print_turn_player_details(self, turn_number):
        print(f"Turn #{turn_number}")
        for player in self.all_players:
            print(
                f"++ Player {player.number} {'(YOU!)' if player.is_me else f'[{len(player.hand)}/{player.size_hand}]'}")
            print(f"      Hand:      {sorted(player.hand)}")
            self.print_cards("      Possibles: ", player.possibles_dict)

    @staticmethod
    def print_cards(prefix: str, cards: dict):
        """
        Prints the cards from a ClueCardSet, separated by category
        :param prefix:
        :param cards:
        """
        s = prefix
        white = f"\n{' ' * len(prefix)}"
        ctr = 0
        for cat in CATEGORIES:
            cat_cards = set(cat.__members__) & cards.get(cat.__name__, set())
            if cat_cards:
                s += f"{white if ctr else ''}{cat.__name__}: {cat_cards}"
                ctr += 1
        print(s)

PICKLE_STATE = 'engine_state.pkl'
PICKLE_GAME = 'game_play.pkl'
ALLOWABLE_INPUTS = ['pass', 'update', 'has', 'lacks']


def handle_input(prompt: str = 'Default Prompt:', splitter: str = ','):
    """
    Input received from user will be a comma-delimited string.
    For all non-numeric entries, check against list of playing cards (e.g. 'White') and other allowed phrases (e.g. 'PASS')
    :param prompt:      The prompt to display to the user
    :param splitter:    The char to split input on
    :return: the original input from user, lower(), once that input has been validated
    """
    while True:
        valid_input = True
        user_input = input(prompt).lower()
        for item in user_input.split(splitter):
            if item.isalpha():
                if item not in ALL_CARDS and item not in ALLOWABLE_INPUTS:
                    valid_input = False
                    print(f" ! ! Unable to recognize input '{item}'. Please try again...")
                    break
        if valid_input:
            break
    return user_input


def main():
    """
    Launch the Engine, which operates from the user's POV in playing the game.
    :return:
    """
    num_players = int(handle_input("Enter Number of Players: "))
    my_player_number = int(handle_input("Enter My Player Num: "))
    my_hand = handle_input("Enter your hand, comma separated: ").split(',')
    eng = Engine(num_players=num_players, my_player_number=my_player_number, my_hand=my_hand)

    def dump_engine_state(*args):
        print(f'Dumping Pickled Engine State to {PICKLE_STATE}')
        with open(PICKLE_STATE, 'wb') as f:
            dill.dump(eng, f)

    def dump_gameplay(*args):
        gameplay_info = [
            eng.num_players,
            eng.my_player_number,
            eng.my_hand,
            eng.turn_sequence
        ]
        print(f'Dumping Gameplay Info to {PICKLE_GAME}')
        with open(PICKLE_GAME, 'wb') as f:
            dill.dump(gameplay_info, f)

    atexit.register(dump_engine_state)
    atexit.register(dump_gameplay)

    eng.run()


if __name__ == '__main__':
    main()
