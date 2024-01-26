import unittest
from unittest import mock, TestCase

import clue_solver
import clue_solver as cs
import defs


class TestGlobalMethods(TestCase):
    @mock.patch("clue_solver.input")
    def test_handle_input(self, mock_input):
        # Test basic valid inputs
        for word in ["1", "rope", "pass"]:
            mock_input.side_effect = [word]
            self.assertEqual(cs.handle_input(), word)

        # A bad entry in a list of cards should prompt the method to ask again
        bad_input_1 = "hall,plum,knief,2"
        bad_input_2 = "hall,plom,knife,2"
        good_input = "hall,plum,knife,2"
        mock_input.side_effect = [bad_input_1, bad_input_2, good_input]
        self.assertEqual(cs.handle_input(), good_input)

        # A good list of cards
        words = "white,hall,green"
        mock_input.side_effect = [words]
        self.assertEqual(cs.handle_input(), words)

        # Check numeric input
        mock_input.side_effect = ["2"]
        self.assertEqual(2, int(cs.handle_input()))

    def test__colorize(self):
        """Verify the method colors a card appropriately"""
        card = defs.SUSPECT.plum
        card_color = defs.COLORMAP[card.__class__.__name__]
        output = cs._colorize(card.name)
        self.assertEqual(output, f"{card_color}{card.name}{defs.COLORS.RESET}")

class EngineTestNoDeductionLogic(TestCase):
    def setUp(self):
        num_players = 4
        my_player_num = 1
        my_hand = ['plum','rope','pipe','hall','study']
        self.engine = cs.Engine(num_players=num_players, my_player_number=my_player_num, my_hand=my_hand)
        self.player1, self.player2, self.player3, self.player4 = self.engine.all_players

    def test_remove_set_from_possibles(self):
        """Verify that all the cards passed in are removed from all Players' .possibles"""
        card = 'dining'
        players = [self.player2, self.player3, self.player4]

        for player in players:
            self.assertTrue(card in player.possibles)

        # Remove card from Players' .possibles
        self.engine.remove_set_from_possibles(players, {card})

        for player in players:
            self.assertFalse(card in player.possibles)

    def test_check_players_hand_size(self):
        """Deduce a Player's .hand if their .hand and .possibles sets are of the appropriate size"""
        # We start out with Player 1 having only .hand, and all other players having only .possibles

        # If (If len(player.hand) + len(player.possibles) != player.hand_size) and
        #   (len(player.hand) != player.hand_size), do nothing.
        player_cards = {}
        for p in self.engine.all_players:
            player_cards[p.number] = {'hand':p.hand, 'possibles':p.possibles}
        # Nothing should be affected when running the method
        self.engine.check_players_hand_size()
        for p in self.engine.all_players:
            self.assertCountEqual(p.hand, player_cards[p.number]['hand'])
            self.assertCountEqual(p.possibles, player_cards[p.number]['possibles'])

        # If len(player.hand) == player.hand_size, clear their player.possibles
        cards = {'dining', 'study', 'conservatory', 'ballroom'}
        self.player4.hand = cards.copy()
        self.assertEqual(len(self.player4.hand), self.player4.hand_size)
        self.assertTrue(len(self.player4.possibles) > 1)
        self.engine.check_players_hand_size()
        self.assertEqual(len(self.player4.possibles), 0)
        self.assertCountEqual(self.player4.hand, cards)

        # If len(player.hand) + len(player.possibles) == player.hand_size, combine both
        #   into player.hand, and remove from all players' .possibles
        self.player3.hand = {'scarlet', 'mustard'}
        self.player3.possibles = {'billiard', 'wrench'}
        self.assertEqual(len(self.player3.hand) + len(self.player3.possibles), 4)

        self.assertTrue('billiard' in self.player2.possibles and 'wrench' in self.player2.possibles)
        self.engine.check_players_hand_size()
        self.assertCountEqual(self.player3.hand, {'scarlet', 'mustard', 'billiard', 'wrench'})
        self.assertEqual(len(self.player3.possibles), 0)
        self.assertFalse('billiard' in self.player2.possibles or 'wrench' in self.player2.possibles)

    @mock.patch("clue_solver.Engine.remove_set_from_possibles")
    @mock.patch("clue_solver.Engine.process_revealed_turn")
    def test_process_turn(self, mock_process, mock_remove):
        """If proceesing a turn returns intel, return True, otherwise False"""
        # Return whatever process_revealed_turn returns
        mock_turn = mock.MagicMock()
        mock_process.return_value = True
        self.assertTrue(self.engine.process_turn(mock_turn))
        mock_remove.assert_called()
        mock_remove.reset_mock()

        mock_process.return_value = False
        self.assertFalse(self.engine.process_turn(mock_turn))
        mock_remove.assert_not_called()

    def test_get_non_revealing_responders(self):
        """Based on Suggester ID and Revealer ID, return all Players in between in gameplay rotation"""
        # No looping around player list
        turn = clue_solver.Turn(number=10, suggester=self.player1, revealer=self.player4)
        responders = self.engine.get_non_revealing_responders(turn)
        self.assertEqual(len(responders), 2)
        self.assertCountEqual(
            [r.number for r in responders],
            [2, 3]
        )

        # Looping around player list
        turn = clue_solver.Turn(number=10, suggester=self.player4, revealer=self.player2)
        responders = self.engine.get_non_revealing_responders(turn)
        self.assertEqual(len(responders), 1)
        self.assertCountEqual(
            [r.number for r in responders],
            [1]
        )

        turn = clue_solver.Turn(number=10, suggester=self.player2, revealer=self.player3)
        responders = self.engine.get_non_revealing_responders(turn)
        self.assertEqual(len(responders), 0)

        # No revealer... return everyone but the suggester
        turn = clue_solver.Turn(number=10, suggester=self.player4, revealer=cs.NOBODY)
        responders = self.engine.get_non_revealing_responders(turn)
        self.assertEqual(len(responders), 3)
        self.assertCountEqual(
            [r.number for r in responders],
            [1, 2, 3]
        )

if __name__ == "__main__":
    unittest.main()
