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
        self.player_list: list[Player] = [Player()]
        self.num_players: int = num_players
        self.my_player_number = my_player_number
        self.my_player: Player = None

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
                print(f"++ Player {player.number} {'(YOU!)' if player == self.my_player else '      '}")
                print(f"      Hand:      {sorted(player.hand)}")
                print(f"      Possibles: {sorted(player.possibles)}")

            print("\n!! Unsolved Turns:")
            for turn in self.turn_sequence[1:]:
                if not turn.totally_processed and turn.revealer is not self.my_player:
                    print(f"   Turn:{turn.number}: Suggester:{turn.suggester.number} Suggestion:"
                          f"{turn.suggestion} Revealer:{turn.revealer.number} Possible Reveals:{turn.possible_reveals}")

            """Player takes turn"""
            print(f"\n-- Player {suggester.number} {'(YOU!)' if suggester == self.my_player else ''} takes turn")
            self.offer_clue_intel()
            self.take_turn(turn_number, suggester)
            self.get_info_from_turns()

            if self.player_is_me(suggester) and self.ready_to_accuse():
                print("****** You are ready to accuse!")
                self.offer_clue_intel()
                break

    def determine_clues(self):
        old_clues = self.accuse_clues.copy()

        all_hands = set()
        hands_and_possibles = set()
        for player in self.player_list:
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
            # TODO this can prob be moved into a method, once I generalize the reduce_* methods
            for player in self.player_list:
                player.possibles -= self.accuse_clues
            # A Clue could also not be a revealed card in a Turn
            for turn in self.turn_sequence:
                turn.possible_reveals -= self.accuse_clues
            # TODO probably want to do asserting for these sets I am changing
            return True

        return False

    def offer_clue_intel(self):
        print(f"-- Known Clues: {self.accuse_clues}")

    def ready_to_accuse(self):
        """For each of the 3 CATEGORIES (Suspect, Weapon, Room), there should be only 1 member whose value is True"""
        # TODO can improve this by breaking down the list by category
        return len(self.accuse_clues) == 3

    def take_turn(self, turn_number, suggester: Player):
        parameters = input("-- Enter Turn Parameters (Suggestion Combo, Revealer Number): ")
        suggestion, revealer_num = parameters.rsplit(sep=',', maxsplit=1)
        revealer_num = int(revealer_num)
        suggestion = suggestion.split(',')
        revealer = self.player_list[revealer_num] if revealer_num > 0 else None
        turn = Turn(number=turn_number, suggestion=suggestion, suggester=suggester, revealer=revealer)

        # If Engine is the player and a card was revealed, store turn.revealed_card for processing
        if revealer is not None and self.player_is_me(suggester):
            revealed_card = input(f"!! Player {suggester.number} is You! What card did you see? ")
            turn.possible_reveals = {revealed_card}
            turn.revealed_card = revealed_card
            # TODO once I refactor logic, this line might go away

        self.turn_sequence.append(turn)

    def get_info_from_turns(self):
        """
        If a pass through the turn sequence yielded new info (narrowing down other players' hands),
            loop through the turn sequence again.
        """
        got_info = True
        while got_info:
            got_info = False
            # Traverse turns reverse-sequentially
            for turn in self.turn_sequence[:0:-1]:
                # TODO ideal loop: reduce turn possibles / get turn reveal -> reduce player possibles / increase
                #  player hand. Also, most of the stuff in process_turn() only needs to happen once!
                got_info |= self.process_turn(turn)
            got_info |= self.determine_clues()

    def process_turn(self, turn: Turn):
        got_info = False

        """
        A 'totally processed' turn is one in which we know that the revealer's HAND overlaps
          with the suggestion, so there's no new information to gain about the revealer's HAND
        """
        if turn.totally_processed:
            return got_info

        responder_sequence = self.get_responder_sequence(turn)
        for responder in responder_sequence:
            if responder == turn.suggester:
                raise ValueError('Responder cannot be Suggester')
            elif responder == turn.revealer:
                if responder == self.my_player:
                    # I revealed a card.
                    turn.possible_reveals = turn.possible_reveals & self.my_player.hand  # Intersection
                    turn.totally_processed = True
                else:
                    # Another player revealed a card.
                    got_info |= self.process_revealed_turn(turn)
                    if turn.revealed_card is not None:
                        self.reduce_player_possibles_from_reveal(turn)
                # There should be no more players to consider after the responder, but break for safety
                break
            else:
                """
                Responder is not the Revealer, so they dont have any of the suggested cards. 
                    Reduce responder's POSSIBLES
                """
                # TODO generalize these reduce_player_possibility methods?
                got_info |= self.reduce_player_possibles_from_pass(responder, turn.suggestion)

        # See if we can deduce a player's entire hand after trimming their POSSIBLES
        got_info |= self.check_players_hand_size()
        got_info |= self.reduce_player_possibles_from_hands()

        if turn.revealer is None:
            # If nobody revealed any card for the turn, all we can do is remove them from players' POSSIBLES,
            #   So no more possible processing can be done.
            turn.totally_processed = True

        return got_info

    def get_responder_sequence(self, turn: Turn):
        sug_num = turn.suggester.number
        rev_num = 0 if (turn.revealer is None) else turn.revealer.number

        if rev_num < 1:  # No revealed card
            return self.player_list[sug_num + 1:] + self.player_list[1:sug_num]
        elif sug_num < rev_num:
            return self.player_list[sug_num + 1:rev_num + 1]
        else:
            return self.player_list[sug_num + 1:] + self.player_list[1:rev_num + 1]

    # TODO Where should this method be called, and where does it not need to be called?
    def reduce_player_possibles_from_hands(self):
        got_info = False
        all_hands = set()
        for player in self.player_list:
            all_hands.update(player.hand)

        for player in self.player_list:
            if len(player.possibles - all_hands) < len(player.possibles):
                got_info = True
                player.possibles -= all_hands
        # TODO I don't like all these methods returning got_info, OR this method could be merged with others. Maybe
        #  theres some redundant "info-checking" going on
        return got_info

    # TODO if info is obtained from this function, what deductions should we do next?
    def check_players_hand_size(self):
        """
        1) If a Player's HAND and POSSIBLES combined is equal to size_hand, make them all part of HAND
        2) If a Player has HAND size equal to size_hand, wipe out their POSSIBLES
        :return: bool Whether a player's entire hand was determined
        """
        got_info = False
        for player in self.player_list:
            # Only want to consider players with unsolved HANDS
            if len(player.hand) == player.size_hand:
                continue

            if len(player.hand) + len(player.possibles) == player.size_hand:
                player.hand.update(player.possibles)
                player.possibles = set()
                got_info = True
        return got_info

    # TODO maybe incorporate this into determine_card_revealed
    def reduce_player_possibles_from_reveal(self, turn: Turn):
        """
        The card that was revealed during a suggestion must be removed from all player's POSSIBLE sets,
            and added to the revealer's HAND
        :param Turn turn:
        :return:
        """
        # Remove from POSSIBLES
        for player in self.player_list:
            player.possibles = player.possibles - {turn.revealed_card}  # Removal of set members

        # Add to HAND
        revealer = turn.revealer
        revealer.hand = revealer.hand | {turn.revealed_card}  # Union

    # TODO all these process methods should prob be consolidated
    # TODO cards as enum.Enum should not break this method
    def process_revealed_turn(self, turn: Turn):
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

        old_possible_reveals = turn.possible_reveals.copy()
        # The revealed card cannot be in the suggester's HAND
        turn.possible_reveals = turn.possible_reveals - set(card for player in self.player_list for card in
                                                            player.hand if player is not turn.suggester)
        # The revealed card must be in the revealer's POSSIBLES
        turn.possible_reveals = turn.possible_reveals & turn.revealer.possibles
        if len(turn.possible_reveals) == 1:
            # We've zeroed in on the revealed card for this turn
            turn.revealed_card = list(turn.possible_reveals)[0]
            turn.totally_processed = True
            return True
        elif len(turn.possible_reveals) < 1:
            print("ERROR: len(turn.possible_reveals) < 1")
            print(f"Turn: {vars(turn)}")
            print(f"old possible_reveals: {old_possible_reveals}")
            print("suggester", vars(turn.suggester))
            print("responder", vars(turn.revealer))
            raise ValueError('turn.possible_reveals has length 0 after reductions')

        # We got information from this turn if we narrowed down the possible_reveals
        return len(turn.possible_reveals) < len(old_possible_reveals)

    def reduce_player_possibles_from_pass(self, player: Player, suggestion: set[str]):
        old_possibles = player.possibles.copy()
        player.possibles = player.possibles - suggestion  # Removal from set
        return len(player.possibles) < len(old_possibles)


def main():
    num_players = int(input("Enter Number of Players: "))
    my_player_number = int(input("Enter My Player Num: "))
    my_hand = input("Enter your hand, comma separated: ").split(',')
    eng = Engine(num_players=num_players, my_player_number=my_player_number, my_hand=my_hand)
    eng.run()


if __name__ == '__main__':
    main()


"""Possible additions to solving logic:"""
# TODO Handle a player passing because they cannot enter a room

# TODO REFACTOR!
    # TODO Come up with the idea of a SET (namedtuple? class?) such that instance == (Suspect,Weapon,Room) I wonder if ultimately I want the "cards" stored in HAND and POSSIBLE to be enum.Enums rather than strings
    # TODO Refactor all code... are all methods in the optimal locations? Can some methods be consolidated?
    # TODO Can some methods be spatially reorganized?
    # TODO cleanup console output... notably the "include in accusation" notes
    # TODO Organize hands according to categories
    # TODO clean up how past Turns are shown
    # TODO maybe still show all past turns, to get a sense of what to suggest

# TODO Spell checking inputs
