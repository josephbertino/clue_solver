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
        # TODO modify the detective pad
        self.detective_pad = {
            category.__name__: {value: True for value in category.__members__} for category in CATEGORIES
        }

        # Initialize player list with blank player
        self.player_list: list[Player] = [Player()]
        self.num_players: int = num_players
        self.my_player_number = my_player_number
        self.my_player: Player = None

        self.setup_players()
        self.reduce_detective_pad()

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

    def run(self):
        turn_number = 0
        while True:
            turn_number += 1
            suggester_num = (turn_number % self.num_players) or self.num_players
            suggester = self.player_list[suggester_num]

            print(f"\nTurn #{turn_number}")
            for player in self.player_list[1:]:
                print(f"++ Player {player.number} {'(YOU!)' if player == self.my_player else '      '}")
                print(f"      Hand:      {sorted(player.hand)}")
                print(f"      Possibles: {sorted(player.possibles)}")

            print("!! Unsolved Turns:")
            for turn in self.turn_sequence[1:]:
                if not turn.totally_processed and turn.revealer is not self.my_player:
                    print(f"   Turn:{turn.number}: Suggester:{turn.suggester.number} Suggestion:"
                          f"{turn.suggestion} Revealer:{turn.revealer.number} Possible Reveals:{turn.possible_reveals}")

            print(f"-- Player {suggester.number} {'(YOU!)' if suggester == self.my_player else ''} suggests")
            self.take_turn(turn_number, suggester)

            # TODO after-turn-deductions and reduce detective pad can be merged i think
            self.after_turn_deductions()
            self.reduce_detective_pad()
            if self.player_is_me(suggester) and self.ready_to_accuse():
                self.make_accusation()
                break

    def player_is_me(self, player: Player):
        return player == self.my_player

    def reduce_detective_pad(self):
        # Mark as "False" all cards appearing in player hands, because they cannot be part of the accusation
        for category_dict in self.detective_pad.values():
            for player in self.player_list:
                for k in category_dict.keys() & player.hand:
                    category_dict[k] = False

        # all_active_cards are all cards in either player HANDS or POSSIBLES... meaning there is still definitely
        #  a chance the card is on the table
        all_active_cards = set()
        for player in self.player_list:
            all_active_cards.update(player.hand | player.possibles)

        # TODO improve the logic for this. I just don't like it
        # Go through each category. If a card is not active, then it must be a Clue
        for category in CATEGORIES:
            clue_contenders = set(category.__members__.keys())
            clue_contenders = clue_contenders - all_active_cards
            if len(clue_contenders) == 1:
                print(f"^^^^^^^^  Include in Accusation: {list(clue_contenders)[0]}")

    # TODO improve logic for this to make it more elegant... it def overlaps with reduce_detective_pad
    def ready_to_accuse(self):
        """For each of the 3 CATEGORIES (Suspect, Weapon, Room), there should be only 1 member whose value is True"""
        for category_dict in self.detective_pad.values():
            if sum(category_dict.values()) == 1:
                print(f"Include in Accusation: {set(k for k,v in category_dict.items() if v)}")
        return all(sum(category_dict.values()) == 1 for category_dict in self.detective_pad.values())

    # TODO this also overlaps with ready_to_accuse and reduce_detective_pad
    def make_accusation(self):
        accusation = []
        for category, category_dict in self.detective_pad.items():
            accusation += [f"{category}: {k}" for k, v in category_dict.items() if v]
        assert len(accusation) == 3
        print(f'**** I should ACCUSE: {accusation}')

    def take_turn(self, turn_number, suggester: Player):
        parameters = input("-- Enter Turn Parameters (Suggestion Combo, Revealer Number): ")
        suggestion, revealer_num = parameters.rsplit(sep=',', maxsplit=1)
        revealer_num = int(revealer_num)
        suggestion = suggestion.split(',')
        revealer = self.player_list[revealer_num] if revealer_num > 0 else None
        turn = Turn(number=turn_number, suggestion=suggestion, suggester=suggester, revealer=revealer)

        # If Engine is the player and a card was revealed, process this turn
        if self.player_is_me(suggester) and revealer is not None:
            revealed_card = input(f"!! Player {suggester.number} is You! What card did you see? ")
            turn.possible_reveals = {revealed_card}
            assert len(turn.possible_reveals) == 1

        self.turn_sequence.append(turn)

    def after_turn_deductions(self):
        """
        If a pass through the turn sequence yielded new info (narrowing down other players' hands),
            loop through the turn sequence again.
        """
        got_info = True
        while got_info:
            got_info = False
            for turn in self.turn_sequence[:0:-1]:
                # Traverse turns reverse-sequentially
                got_info |= self.process_turn(turn)

    def get_responder_sequence(self, turn: Turn):
        sug_num = turn.suggester.number
        rev_num = 0 if (turn.revealer is None) else turn.revealer.number

        if rev_num < 1:  # No revealed card
            return self.player_list[sug_num+1:] + self.player_list[1:sug_num]
        elif sug_num < rev_num:
            return self.player_list[sug_num+1:rev_num+1]
        else:
            return self.player_list[sug_num+1:] + self.player_list[1:rev_num+1]

    def process_turn(self, turn: Turn):
        got_info = False

        """
        A 'totally processed' turn is one in which we know that the revealer's HAND overlaps
          with the suggestion, so there's no new information to gain about the revealer's HAND
        """
        if turn.totally_processed:
            return got_info

        suggester = turn.suggester
        responder_sequence = self.get_responder_sequence(turn)
        for responder in responder_sequence:
            if responder == suggester:
                raise ValueError('Responder cannot be Suggester')
            elif responder == turn.revealer:
                if responder == self.my_player:
                    # I revealed a card... nothing more can be gained from this turn
                    turn.possible_reveals = turn.possible_reveals & self.my_player.hand  # Intersection
                    turn.totally_processed = True
                else:
                    # Another player revealed a card. Try to find out who
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
                got_info |= self.reduce_player_possibles_from_pass(responder, turn.suggestion)

        # TODO should this go somewhere else?
        self.check_players_hand_size()

        if turn.revealer is None:
            # If nobody revealed any card for the turn, all we can do is remove them from players' POSSIBLES
            turn.totally_processed = True

        return got_info

    def check_players_hand_size(self):
        """
        1) If a Player's HAND and POSSIBLES combined is equal to size_hand, make them all part of HAND
        2) If a Player has HAND size equal to size_hand, wipe out their POSSIBLES
        """
        for player in self.player_list:
            if len(player.hand) + len(player.possibles) == player.size_hand:
                player.hand.update(player.possibles)
            if len(player.hand) == player.size_hand:
                player.possibles = set()

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

    # TODO my logic sucks at this point. too complicated. need to refactor a lot
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


"""
Possible additions to solving logic:
    0) If something is Known, remove it from all possible reveals and player.possibles
    
    1) REFACTOR!
        # TODO Come up with the idea of a SET (namedtuple? class?) such that instance == (Suspect,Weapon,Room)
            + I wonder if ultimately I want the "cards" stored in HAND and POSSIBLE to be enum.Enums rather than strings
        # TODO Refactor all code... are all methods in the optimal locations? Can some methods be consolidated?
        # TODO Can some methods be spatially reorganized?
        # TODO cleanup console output... notably the "include in accusation" notes
    
    # TODO Improve detective pad
        # TODO If all but one elem from a category is in players HANDS, then THAT has to be the culprit!
        # TODO if an elem is missing from hands and possibles, then THAT has to be the culprit!
    # TODO Handle a player passing because they cannot enter a room
    # TODO Organize hands according to categories
    # TODO Spell checking inputs
"""
