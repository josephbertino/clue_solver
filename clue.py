import enum

SUSPECT = enum.Enum('Suspect', ['white', 'plum', 'peacock', 'scarlet', 'mustard', 'green'])
WEAPON = enum.Enum('Weapon', ['rope', 'pipe', 'wrench', 'candlestick', 'knife', 'revolver'])
ROOM = enum.Enum('Room', ['billiard', 'lounge', 'conservatory', 'kitchen', 'hall',
                          'dining', 'study', 'library', 'ballroom'])
CATEGORIES = [SUSPECT, WEAPON, ROOM]
ALL_CARDS = {value for category in CATEGORIES for value in category.__members__}
NUM_CARDS = len(ALL_CARDS)

class Player(object):
    def __init__(self, idx: int, size_hand: int, is_me=False, hand=None):
        if hand is None:
            hand = []
        self.size_hand = size_hand
        self.idx = idx
        self.hand: set[str] = set(hand if is_me else [])
        self.possibles: set[str] = set([] if is_me else ALL_CARDS - set(hand))


class Turn(object):
    def __init__(self, suggestion: list[str], suggester_idx, revealer_idx):
        self.suggestion: set[str] = set(suggestion)
        self.possible_reveals: set[str] = set(suggestion)
        self.suggester_idx: int = suggester_idx
        self.revealer_idx: int = revealer_idx
        self.revealed_card = None
        self.totally_processed = False


class Engine:
    def __init__(self, num_players, my_player_num, my_hand):
        self.turn_sequence: list[Turn] = []
        self.detective_pad = {
            category.__name__: {value: True for value in category.__members__} for category in CATEGORIES
        }

        self.num_players: int = num_players
        self.player_list: list[Player] = []
        self.my_player: Player = None
        self.my_hand: list[str] = my_hand

        self.setup_players(my_player_num)
        self.reduce_detective_pad()

    def setup_players(self, my_player_num):
        num_active_cards = NUM_CARDS - 3
        cards_per_player = num_active_cards // self.num_players
        leftovers = num_active_cards % self.num_players
        self.player_list = []
        for i in range(self.num_players):
            is_me = i == (my_player_num - 1)
            size_hand = cards_per_player + (1 if i < leftovers else 0)
            new_player = Player(idx=i, size_hand=size_hand, is_me=is_me, hand=self.my_hand)
            if is_me:
                self.my_player = new_player
            self.player_list.append(new_player)

    def run(self):
        turn_number = 0
        while True:
            suggester_idx = turn_number % self.num_players
            player = self.player_list[suggester_idx]

            print(f"\nTurn #{turn_number+1}")
            for player in self.player_list:
                print(f"++ Player {player.idx+1} {'(YOU!)' if player == self.my_player else '      '} || Hand: {player.hand}")
                print(f"          Possibles: {player.possibles}")

            print(f"?? Player {suggester_idx+1} suggests")
            self.take_turn(suggester_idx)
            self.after_turn_deductions()

            # Determine if you are ready to accuse
            self.reduce_detective_pad()
            if self.player_is_me(player) and self.ready_to_accuse():
                self.make_accusation()
                break

            turn_number += 1

    def player_is_me(self, player):
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

        # Go through each category. If a card is not in any players' POSSIBLES or HAND, then it must be a Clue
        for category in CATEGORIES:
            clue_contenders = set(category.__members__.keys())
            clue_contenders = clue_contenders - all_active_cards
            if len(clue_contenders) == 1:
                print(f"^^^^^^^^  Include in Accusation: {list(clue_contenders)[0]}")


    def ready_to_accuse(self):
        """For each of the 3 CATEGORIES (Suspect, Weapon, Room), there should be only 1 member whose value is True"""
        for category_dict in self.detective_pad.values():
            if sum(category_dict.values()) == 1:
                print(f"Include in Accusation:")
        return all(sum(category_dict.values()) == 1 for category_dict in self.detective_pad.values())

    def make_accusation(self):
        accusation = []
        for category, category_dict in self.detective_pad.items():
            accusation += [f"{category}: {k}" for k, v in category_dict.items() if v]
        assert len(accusation) == 3
        print(f'**** I should ACCUSE: {accusation}')

    def take_turn(self, suggester_idx):
        parameters = input("-- Enter Turn Parameters (Suggestion Combo, Responder Number): ")
        suggestion, revealer_idx = parameters.rsplit(sep=',', maxsplit=1)
        suggestion = suggestion.split(',')
        revealer_idx = int(revealer_idx) - 1
        turn = Turn(suggestion=suggestion, suggester_idx=suggester_idx, revealer_idx=revealer_idx)

        # If Engine is the player, and saw a revealed card, specially process this turn
        suggester = self.player_list[suggester_idx]
        if self.player_is_me(suggester) and revealer_idx >= 0:
            revealed_card = input(f"!! Player {suggester_idx+1} is You! What card did you see? ")
            turn.possible_reveals = {revealed_card}  # Intersection
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
            for turn in self.turn_sequence[::-1]:
                # Traverse turns reverse sequentially
                got_info |= self.process_turn(turn)

    def process_turn(self, turn):
        got_info = False

        """
        A 'totally processed' turn is one in which we know that the revealer's HAND overlaps
          with the suggestion, so there's no new information to gain about the revealer's HAND
        """
        if turn.totally_processed:
            return got_info

        suggester = self.player_list[turn.suggester_idx]
        responder_sequence = self.player_list[turn.suggester_idx + 1:] + self.player_list[:turn.suggester_idx]
        for responder in responder_sequence:
            if responder.idx != turn.revealer_idx:
                """
                Responder is not the Revealer, so they dont have any of the suggested cards. 
                    Reduce responder's POSSIBLES
                """
                got_info |= reduce_player_possibles_from_pass(responder, turn.suggestion)
            else:
                revealed_card = determine_revealed_card(turn, suggester, responder)
                if revealed_card:
                    self.reduce_player_possibles_from_reveal(turn, revealed_card)
                    got_info = True
                break

        # See if there is
        self.check_players_hand_size()

        if turn.revealer_idx < 0:
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
    def reduce_player_possibles_from_reveal(self, turn: Turn, revealed_card: str):
        """
        :param revealed_card: The card that was revealed during a suggestion.
            It must be removed from all player's POSSIBLE sets, and added
            to the revealer's HAND

        :return:
        """
        # Remove from POSSIBLES
        for player in self.player_list:
            player.possibles = player.possibles - {revealed_card}  # Removal of set members

        # Add to HAND
        revealer = self.player_list[turn.revealer_idx]
        revealer.hand = revealer.hand | {turn.revealed_card}  # Union


def reduce_player_possibles_from_pass(player: Player, suggestion: set[str]):
    old_possibles = player.possibles.copy()
    player.possibles = player.possibles - suggestion  # Removal from set
    return len(player.possibles) < len(old_possibles)


# TODO cards as enum.Enum should not break this method
def determine_revealed_card(turn: Turn, suggester: Player, responder: Player):
    if turn.possible_reveals & responder.hand:  # Intersection
        # At least one of the cards in the suggestion are already in the responder's known hand.
        #   We can't get any more information from this turn
        turn.possible_reveals = turn.possible_reveals & responder.hand  # Intersection
        turn.totally_processed = True
        return None

    """
    Potentially shrink possible reveals for this turn'S suggestion:
      We know that the revealed card CAN'T be in the suggester's hand,
      And MUST be in the responder's hand.
    """
    old_possible_reveals = turn.possible_reveals.copy()
    turn.possible_reveals = (turn.possible_reveals - suggester.hand) & responder.possibles
    if len(turn.possible_reveals) == 1:
        # We've zeroed in on what the responder revealed in this turn
        turn.revealed_card = turn.possible_reveals.pop()
        turn.totally_processed = True
        return turn.revealed_card
    elif len(turn.possible_reveals) < 1:
        print(f"Turn: {vars(turn)}")
        print(f"old possible_reveals: {old_possible_reveals}")
        print("suggester", vars(suggester))
        print("responder", vars(responder))
        raise ValueError('turn.possible_reveals has length 0 after reductions')

    return None


def main():
    num_players = int(input("Enter Number of Players: "))
    my_player_num = int(input("Enter My Player Num: "))
    my_hand = input("Enter your hand, comma separated: ").split(',')
    eng = Engine(num_players=num_players, my_player_num=my_player_num, my_hand=my_hand)
    eng.run()

if __name__ == '__main__':
    main()


"""
Possible additions to solving logic:
    
    1) REFACTOR!
        # TODO Come up with the idea of a SET (namedtuple? class?) such that instance == (Suspect,Weapon,Room)
            + I wonder if ultimately I want the "cards" stored in HAND and POSSIBLE to be enum.Enums rather than strings
        # TODO Refactor all code... are all methods in the optimal locations? Can some methods be consolidated?
        # TODO Can some methods be spatially reorganized?
        # TODO cleanup console output
    
    # TODO Improve detective pad
    # TODO Handle a player passing because they cannot enter a room
    # TODO Organize hands according to categories
    # TODO Spell checking inputs
"""