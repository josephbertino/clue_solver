# clue_solver

Python utility to **help you** solve the board game Clue.

It does not play the game for you, meaning it does not come up with suggestions on your turn!
All it really does is perform all the deductions of who-has-what based on the information made available to everyone during gameplay. That information being: who made a suggestion during a Turn and who (if anyone) showed them a card in response.

Think of this utility as applying the principles of card counting to playing a kid's board/card game. Enjoy!

# How to use the engine

Run file `clue.py` from the console or on your IDE of choice.

# Important considerations during gameplay

* When dealing cards face-down to Players, deal cards one at a time in Round Robin order: Player 1 gets one card, then Player 2, then Player 3, etc.
  * This is important because the game keeps track of the size of each Player's hand. And depending on the number of Players, not all Players will have the same number of cards in their hand. E.g. when there are 4 Players, two will have 5 cards in their hand and two will have 4.
  * So when there are 'leftover' cards, the First players in the rotation (starting with Player 1) must have those extra cards
* If a Player does not enter a room and make a suggestion during their Turn, this is considered a "Pass". Please do not forget to enter "pass" for a Player's Turn into the Engine.