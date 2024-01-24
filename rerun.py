import dill
from defs import Turn
from clue_solver import Engine, PICKLE_GAME


def get_turn_players(eng: Engine, turn: Turn):
    eng_suggester = eng_revealer = None
    if turn.suggester:
        eng_suggester = eng.get_player(turn.suggester.number)
    if turn.revealer:
        eng_revealer = eng.get_player(turn.revealer.number)
    return eng_suggester, eng_revealer


def main():
    with open(PICKLE_GAME, 'rb') as f:
        game_info = dill.load(f)

    # Unpack pickled state
    num_players, my_player_num, my_hand, turn_sequence = game_info
    eng = Engine(num_players, my_player_num, my_hand)
    for turn in turn_sequence[1:]:  # Skip Turn 0; eng already has it
        eng_suggester, eng_revealer = get_turn_players(eng, turn)
        new_turn = Turn(
            number=turn.number,
            suggestion=turn.suggestion,
            suggester=eng_suggester,
            revealer=eng_revealer,
            is_pass=turn.is_pass,
        )
        if new_turn.suggester and new_turn.suggester.is_me:
            new_turn.revealed_card = turn.revealed_card
        eng.one_time_turn_deductions(new_turn)
        eng.turn_sequence.append(new_turn)

    # Process all turns for info
    eng.process_turns_for_info()

    # Resume play from where you left off
    eng.run()


if __name__ == '__main__':
    main()
