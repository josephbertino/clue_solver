# TODOs (For Developer Eyes Only)

These are some additional ideas I have to improve the experience of using this Clue Solver Tool

+ Write more unit tests for the Engine

+ Put logic in, where if we've solved for a category, and only one Player has a non-murder card from that category in their POSSIBLES, then that Player must have that card in their HAND

+ rename all `*_num` variables as `*_id`, since that is more descriptive 

+ In offer_turn_intel(), don't show turns where the user was the Revealer

+ Disable ANSI escape codes on terminals that don't support them

+ Maybe just tell the engine how many cards each player has, when setting up the game, rather than relying on the user and their peers to deal the cards out in the "correct" order

+ Make a UI
