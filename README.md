# Clue Board Game "Solver"

## What Does It Do?
This is a utility written in Python to help you win at the board game Clue (aka Cluede outside the US).

As you play Clue, whether virtually or in-person, you use the tool to manually enter the details about each successive Turn taken during the game. Such Turn details includes the Player who is making a suggestion about the murder, the Player who reveals a card to refute that suggestion (if any), or if a Player does not make a suggestion on a given Turn. 

The tool keeps track of Turn order, the cards in your hand, and what it knows about the other Players' hands. As more details become available with successive Turns, the tool uses deep process of elimination to deduce what other Players are holding. With enough Turns, it will be able to deduce the winning suggestion for you.

Think of this utility as applying the principles of card counting to playing a kid's board/card game. Enjoy!

**Please Note**: This tool does not play the game for you, meaning it does not tell you what to guess on your Turn. However, you WILL be empowered to make better guesses with the details provided by this tool!

## How do I start using it?

1. Download this project `clue_solver` to your desktop
2. In a terminal or console, navigate to this project's folder and run the file `clue.py`
```term
>>> python clue.py
```
3. Follow the prompts in the terminal to set up the game and begin playing!
    + See the section below [Setting up the Game](#setting-up-the-game) for more details

## Setting Up The Game

<figure>
    <img src="sources/setup_screen.png" width="900" height="400">
    <figcaption>Setup screen when you startup the Clue Solver tool</figcaption>
</figure>

When starting the tool, it will ask you to enter the following details:

    1. The total number of players
    2. Your "Player Number", where you are in the rotation (1, 2, 3,...)
    3. The cards in your hand

**When Dealing Cards to Players**
+ **Please Note** that the tool determines the size of each Player's hand based on the total number of players and the known size of the active deck (18 cards, not including the 3 hidden cards that comprise the solution). Depending on the number of Players, not all Players will have the same number of cards in their hand. E.g. when there are 4 Players, two will have 5 cards in their hand and two will have 4.
* Deal cards one at a time in Round Robin order: Player 1 gets one card, then Player 2, then Player 3, etc.
  * When there are 'leftover' cards, they should be distributed to the first players in the rotation (starting with Player 1)

**The Cards, according to Clue Solver**
* This tool assumes the following naming of Suspects, Weapons, and Rooms. 
  * SUSPECT = ['white', 'plum', 'peacock', 'scarlet', 'mustard', 'green']
  * WEAPON = ['rope', 'pipe', 'wrench', 'candlestick', 'knife', 'revolver']
  * ROOM = ['billiard', 'lounge', 'conservatory', 'kitchen', 'hall', 'dining', 'study', 'library', 'ballroom']
* If you are playing a variant that differs in the makeup of these categories, the only change you must make is in the `./defs.py` module. The rest will sort itself out automatically.

**Entering Your Hand at the Game's Start**
  + Enter the contents of your hand as they appear in the lists `SUSPECT`, `WEAPON`, and `ROOM` defined in `./defs.py`
    + e.g. the Lead Pipe should simply be entered as `pipe`
    + e.g. Colonel Mustard should be entered as `mustard`
  + No whitespace, only alpha-strings separated by commas, and order does not matter
  + Example with a four-card hand: `white,conservatory,knife,plum`

## Gameplay

<what the details look like>
<entering a turn>
<when the tool gives you hints>

* If a Player does not enter a room and make a suggestion during their Turn, this is considered a "Pass". Please do not forget to enter "pass" for a Player's Turn into the Engine.


# How to enter hands and other turn instructions

**Enter a Turn Suggestion + Revealer Information**
  + Entry must be comma-separated and without spaces
  + Format: `card_1,card_2,card_3,revealer_number`
    + e.g. 'billiard,plum,knife,2'
    + If the suggestion went around without any Player making a reveal, enter `0` for the `revealer_number`

**Passing on a Turn (the Player does not make a suggestion)**
  + Enter: 'pass'

## Advanced Engine Interactions

**Manually Updating a Player's Hand Mid-Turn**
  + Enter: 'update'
  + Then enter a line of the format (comma-separated, no spaces)
    + `<player_num>,[has|lacks],<card>`
    + e.g. '2,lacks,rope'



## Questions?

I'd love to know what you think!

+ Email: joseph.bertino@gmail.com
+ LinkedIn: http://linkedin.com/in/joseph-bertino
+ Instagram: @yetixhunting