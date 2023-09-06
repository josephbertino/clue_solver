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

* This Engine assumes the following sets of Suspects, Weapons, and Rooms. If you are playing a variant that differs in the makeup of these categories, the only change you must make is in the `defs` module. The rest will sort itself out automatically.
  * SUSPECT = ['white', 'plum', 'peacock', 'scarlet', 'mustard', 'green']
  * WEAPON = ['rope', 'pipe', 'wrench', 'candlestick', 'knife', 'revolver']
  * ROOM = ['billiard', 'lounge', 'conservatory', 'kitchen', 'hall', 'dining', 'study', 'library', 'ballroom']

# How to enter hands and other turn instructions

**Enter Your Hand at the Game's Start**
  + Enter the contents of your hand as "cards" from the `SUSPECT`, `WEAPON`, or `ROOM` lists defined in `defs.py`.
  + No whitespace, only alpha-strings separated by commas
  + Format: `card1,card2,card3...`

**Enter a Turn Suggestion + Revealer Information**
  + Entry must be comma-separated and without spaces
  + Format: `card_1,card_2,card_3,revealer_number`
    + e.g. 'billiard,plum,knife,2'
    + If the suggestion went around without any Player making a reveal, enter `0` for the `revealer_number`

**Passing on a Turn (the Player does not make a suggestion)**
  + Enter: 'pass'

**Manually Updating a Player's Hand Mid-Turn**
  + Enter: 'update'
  + Then enter a line of the format (comma-separated, no spaces)
    + `<player_num>,[has|lacks],<card>`
    + e.g. '2,lacks,rope'
