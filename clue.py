import enum

SUSPECT = enum.Enum('Suspect', ['white', 'plum', 'peacock', 'scarlet', 'mustard', 'green'])
WEAPON = enum.Enum('Weapon', ['rope', 'pipe', 'wrench', 'candlestick', 'knife', 'revolver'])
ROOM = enum.Enum('Room', ['billiard', 'lounge', 'conservatory', 'kitchen', 'hall',
                          'dining', 'study', 'library', 'ballroom'])
CATEGORIES = [SUSPECT, WEAPON, ROOM]
ALL_CARDS = {value for category in CATEGORIES for value in category.__members__}
NUM_CARDS = len(ALL_CARDS)


class Player(object):
    def __init__(self, number=0, size_hand=0, is_me=False, hand=None):
        if hand is None:
            hand = []
        self.size_hand = size_hand
        self.number = number
        self.hand: set[str] = set(hand if is_me else [])
        self.possibles: set[str] = set([] if is_me else ALL_CARDS - set(hand))

        if number == 0:  # Non-player should have empty sets
            self.hand = set([])
            self.possibles = set([])


class Turn(object):
    def __init__(self, number: int = 0, suggestion=None, suggester: Player = None,
                 revealer: Player = None):
        if suggestion is None:
            suggestion = set()
        self.number = number
        self.suggestion: set[str] = set(suggestion)
        self.possible_reveals: set[str] = set(suggestion)
        self.suggester: Player = suggester
        self.revealer: Player = revealer
        self.revealed_card = None
        self.totally_processed = False


class Engine:
    def __init__(self, num_players, my_player_number, my_hand):
        # Initialize turn list with blank turn
        self.turn_sequence: list[Turn] = [Turn()]
        self.my_hand: list[str] = my_hand
        self.accuse_clues = set()

        # Initialize player list with blank player
        # TODO how to solve the player_list[1:] fiasco everywhere
        self.player_list: list[Player] = [Player()]
        self.num_players: int = num_players
        self.my_player_number = my_player_number
        self.my_player = None

        self.setup_players()

    def setup_players(self):
        num_active_cards = NUM_CARDS - 3
        cards_per_player = num_active_cards // self.num_players
        leftovers = num_active_cards % self.num_players
        for i in range(1, self.num_players + 1):
            is_me = i == self.my_player_number
            size_hand = cards_per_player + (1 if i <= leftovers else 0)
            new_player = Player(number=i, size_hand=size_hand, is_me=is_me, hand=self.my_hand)
            if is_me:
                self.my_player = new_player
            self.player_list.append(new_player)

    def player_is_me(self, player: Player):
        return player == self.my_player

    def run(self):
        turn_number = 0
        while True:
            turn_number += 1
            suggester_num = (turn_number % self.num_players) or self.num_players
            suggester = self.player_list[suggester_num]

            """Log game details to output"""
            print(f"\n----------------------------------------------------------")
            print(f"Turn #{turn_number}")
            for player in self.player_list[1:]:
                print(f"++ Player {player.number}{' (YOU!)' if self.player_is_me(player) else f' [{len(player.hand)}/{player.size_hand}]'}")
                print(f"      Hand:      {sorted(player.hand)}")
                print(f"      Possibles: {sorted(player.possibles)}")

            self.offer_clue_intel()

            if self.take_turn(turn_number, suggester):
                self.process_turns_for_info()

            if self.player_is_me(suggester) and self.ready_to_accuse():
                print("****** You are ready to accuse!")
                self.offer_clue_intel()
                break

    def take_turn(self, turn_number, suggester: Player):
        """

        :param turn_number:
        :param suggester:
        :return bool: True if turn was taken, False if player passed
        """
        """Player takes turn"""
        print(f"\n-- Player {suggester.number} {'(YOU!)' if suggester == self.my_player else ''} takes turn")

        parameters = input("-- Enter Turn Parameters (Suggestion Combo + Revealing Player Number, or 'PASS'): ")
        if parameters.upper().strip() == 'PASS':
            return False

        suggestion, revealer_num = parameters.rsplit(sep=',', maxsplit=1)
        revealer_num = int(revealer_num)
        suggestion = suggestion.split(',')
        revealer = self.player_list[revealer_num] if revealer_num > 0 else None
        turn = Turn(number=turn_number, suggestion=suggestion, suggester=suggester, revealer=revealer)

        self.one_time_turn_deductions(turn)
        self.turn_sequence.append(turn)
        return True

    def one_time_turn_deductions(self, turn: Turn):
        """Perform post-turn deductions that only need to happen once, immediately after a turn"""
        # Non-revealing responders from a turn don't have any of the suggested cards. Reduce their POSSIBLES
        self.remove_set_from_player_possibles(players=self.get_non_revealing_responders(turn), cards=turn.suggestion)

        # A 'totally processed' turn is one in which we know that the revealer's HAND overlaps
        #   with the suggestion (which happens automatically when there is no revealer, or the revealer is Me),
        #   so there's no new information to gain about the revealer's HAND from further processing
        if self.player_is_me(turn.revealer) or turn.revealer is None:
            turn.totally_processed = True
        elif self.player_is_me(turn.suggester):
            # If I was the suggester and a card was revealed, store turn.revealed_card
            revealed_card = input(f"!! Player {turn.suggester.number} is You! What card did you see? ")
            turn.possible_reveals = {revealed_card}
            turn.revealed_card = revealed_card

    def get_non_revealing_responders(self, turn: Turn):
        """
        Return the sequence of players ("responders") in a turn that "passed" on a suggestion (did not have a clue card),
            up until but NOT including the clue revealer
        :param Turn turn:
        :return list[Player]:
        """
        sug_num = turn.suggester.number
        rev_num = 0 if (turn.revealer is None) else turn.revealer.number

        if rev_num < 1:  # No revealed card... return everyone BUT the suggester
            return self.player_list[sug_num + 1:] + self.player_list[1:sug_num]
        elif sug_num < rev_num:
            return self.player_list[sug_num + 1:rev_num]
        else:
            return self.player_list[sug_num + 1:] + self.player_list[1:rev_num]

    def determine_clues(self):
        old_clues = self.accuse_clues.copy()

        all_hands = set()
        hands_and_possibles = set()
        for player in self.player_list[1:]:
            all_hands.update(player.hand)
            hands_and_possibles.update(player.hand | player.possibles)

        for category in CATEGORIES:
            # If all but one card from a category is in players' HANDS, the outcast must be a Clue
            cat_cards_not_in_hands = set(category.__members__.keys()) - all_hands
            if len(cat_cards_not_in_hands) == 1:
                # TODO can section accuse_clues by category
                self.accuse_clues.update(cat_cards_not_in_hands)
            elif len(cat_cards_not_in_hands) < 1:
                raise ValueError(f"All cards from the same category are in play, which is impossible!: {category.__name__}")

            # If a card is not in any HANDS or POSSIBLES, it must be a Clue
            inactive_cat_cards = set(category.__members__.keys()) - hands_and_possibles
            if len(inactive_cat_cards) == 1:
                self.accuse_clues.update(inactive_cat_cards)
            elif len(inactive_cat_cards) > 1:
                raise ValueError(f"Multiple cards from the same category are out of play!: {category.__name__}:{inactive_cat_cards}")

        if len(self.accuse_clues) > len(old_clues):
            # If we gained a new clue, make sure it's removed from player POSSIBLES
            #    (We may have determined a clue because all other cards in that category were in player HANDS...
            #    in which case that card might still be lingering in a player's POSSIBLE)
            self.remove_set_from_player_possibles(players=self.player_list[1:], cards=self.accuse_clues)

            # A Clue could also not be a revealed card in a Turn
            for turn in self.turn_sequence:
                turn.possible_reveals -= self.accuse_clues
            # TODO probably want to do asserting for these sets I am changing
            return True

        return False

    def offer_clue_intel(self):
        print(f"\n** Known Clues: {self.accuse_clues}")
        print("\n?? Unsolved Turns:")
        for turn in self.turn_sequence[1:]:
            if not turn.totally_processed:
                print(
                    f"   Turn:{turn.number}: Suggester:{turn.suggester.number} Revealer:{turn.revealer.number} Possible Reveals:{turn.possible_reveals}")

    def ready_to_accuse(self):
        """For each of the 3 CATEGORIES (Suspect, Weapon, Room), there should be only 1 member whose value is True"""
        # TODO can improve this by breaking down the list by category
        return len(self.accuse_clues) == 3

    def process_turns_for_info(self):
        """
        If a pass through the turn sequence yielded new info (narrowing down other players' hands),
            loop through the turn sequence again.
        """
        got_info = True
        while got_info:
            got_info = False
            # Traverse turns reverse-sequentially
            for turn in self.turn_sequence[:0:-1]:
                if not turn.totally_processed:
                    got_info |= self.process_turn(turn)
            got_info |= self.determine_clues()

    def process_turn(self, turn: Turn):
        if self.process_revealed_turn(turn):
            # We added to our knowledge of a player's HAND
            self.remove_set_from_player_possibles(players=self.player_list[1:], cards={turn.revealed_card})
            self.reduce_player_possibles_from_hands()
            self.check_players_hand_size()
            return True
        return False

    # TODO cards as enum.Enum should not break this method
    @staticmethod
    def process_revealed_turn(turn: Turn):
        """
        Potentially shrink possible reveals for this turn's suggestion:
          We know that the revealed card CAN'T be in any other player's HAND,
          And MUST be in the revealer's POSSIBLES.
        :return: bool
        """
        if turn.possible_reveals & turn.revealer.hand:  # Intersection
            # At least one of the cards in the suggestion are already in the responder's known hand.
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
        1) If a Player's HAND and POSSIBLES combined is equal to size_hand, make them all part of HAND
        2) If a Player has HAND size equal to size_hand, wipe out their POSSIBLES
        :return: bool Whether a player's entire hand was determined
        """
        got_info = False
        for player in self.player_list[1:]:
            # Only want to consider OTHER players with unsolved HANDS
            if self.player_is_me(player):
                continue

            if len(player.hand) == player.size_hand and len(player.possibles) > 0:
                # Reduce player.possibles is a gain in information
                player.possibles = set()
                got_info = True
            elif len(player.hand) + len(player.possibles) == player.size_hand:
                player.hand.update(player.possibles)
                player.possibles = set()
                got_info = True
        return got_info

    def reduce_player_possibles_from_hands(self):
        got_info = False
        all_hands = set()
        for player in self.player_list[1:]:
            all_hands.update(player.hand)

        # TODO don't like having player_list[1:] everywhere, but also don't like 0-indexing...
        for player in self.player_list[1:]:
            if len(player.possibles - all_hands) < len(player.possibles):
                got_info = True
                player.possibles -= all_hands
        return got_info

    @staticmethod
    def remove_set_from_player_possibles(players: list[Player], cards: set[str]):
        for player in players:
            player.possibles -= cards  # Removal from set


def main():
    num_players = int(input("Enter Number of Players: "))
    my_player_number = int(input("Enter My Player Num: "))
    my_hand = input("Enter your hand, comma separated: ").split(',')
    eng = Engine(num_players=num_players, my_player_number=my_player_number, my_hand=my_hand)
    eng.run()


if __name__ == '__main__':
    main()


"""Possible additions to solving logic:"""
# TODO if a clue is found, try to pinpoint who has non-clue cards (e.g. if the Wrench is the Weapon Clue,
#  and the Knife is only in one person's POSSIBLES, then it must be in their HAND!

# TODO REFACTOR!
    # TODO Come up with the idea of a SET (namedtuple? class?) such that instance == (Suspect,Weapon,Room) I wonder if ultimately I want the "cards" stored in HAND and POSSIBLE to be enum.Enums rather than strings
    # TODO cleanup console output... notably the "include in accusation" notes
    # TODO Organize hands according to categories
    # TODO reconsider how past Turns are shown
    # TODO maybe still show all past turns, to get a sense of what to suggest

# TODO Spell checking inputs
