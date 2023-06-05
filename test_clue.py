import unittest
from unittest import mock, TestCase

import clue
from clue import *


class TestGlobalMethods(TestCase):

    @mock.patch('clue.input')
    def test_handle_input(self, mock_input):
        # Test basic valid inputs
        for word in ['1', 'rope', 'pass']:
            mock_input.side_effect = [word]
            self.assertEqual(clue.handle_input(), word)

        # A bad entry in a list of cards
        mock_input.side_effect = ['hall,plum,knief,2',
                                  'hall,plum,knife,2']
        self.assertEqual(clue.handle_input(), 'hall,plum,knife,2')

        # A good list of cards
        words = 'white,hall,green'
        mock_input.side_effect = [words]
        self.assertEqual(clue.handle_input(), words)

        # Check numeric input
        mock_input.side_effect = ['2']
        self.assertEqual(2, int(clue.handle_input()))


if __name__ == '__main__':
    unittest.main()