# Level format
# # = wall, @ = player, + = player on goal, $ = crystal, * = crystal on goal, . = goal, ' ' = floor
# P = push mask, B = break mask, I = ignore mask
# rules: each level must be solvable be surrounded by walls

level_str_hard2: str = """

###########
####...####
#P$$$$$$$B#
#$#.$$$.#$#
#$#.$#$.#$#
#$#.$$$.#$#
#I#######$#
#@$.$.$.$$#
###########
"""

level_str_hard1: str = """
############
#.##P###B######
#$##@###  ######
#.$  $. $ ######
#$##$# ## ######
#.$  $. $ ######
#$#   ### ######
#     ########
###############
"""

level_str_medium3: str = """
################
#     B    #####
#$######## #####
#$$$$$####    I#
# #$######@#####
#*$##.P$$  $.###
#.$#############
#####
"""


level_str_medium2: str = """
###############
######B    #####
######$### #####
#$$$$$$### #####
#$####$###@#####
#*   $  $  #####
#. ####### #####
########## #####
########P  #####
################
"""

level_str_medium1: str = """
################
######B    #####
######$### #####
######$### #####
######$###@#####
##...$  $  $$$$#
########## ###$#
########## ###$#
########## ###$#
########## $$$P#
################
"""


level_str_all_masks_tutorial: str = """
########
#####P###
#.$ $@ .#
##B#.$$##_-1_look, a red mask->
##$##I.#
##$#####
##.#####_4_hit 'R' if stuck
########
"""

level_str_ignore_tutorial: str = """
########_4_use 'R' to restart the level if you get stuck
#####P##
#.$ $@ #_-2_hit <space> to switch mask
####.$$#
#####I.#_2_look, a new kind of mask ->
########

"""


level_str_push_tutorial: str = """
######_4_Each glowy tile must be covered by a crystal!
####P#####
#.$ @ $.#
#########_4_otherwise Diablo will escape hell and destroy the World!
"""

game_menu: str = """
#####_2_Welcome Maztek Spirit Warrior!
#   #
# @ #_6_Use WASD keys to move
#   #
##P#_-1_pick up this mask ->
## #_-1_so you can push crystals
## #######_6_Push the crystal to start a New Game!
##  $.#
## #######
## #_6_Credits:
## #
## #_6_Programming: Tomas Balyo, ChatGPT
## #
## #_6_Music and Sound: Meinrad Weiler
## #
## #_6_Level design: Mihai Herda
## #
## #_6_Graphics: ChatGPT, Grok
####
"""

all_levels = [level_str_all_masks_tutorial, game_menu, level_str_push_tutorial, level_str_ignore_tutorial, level_str_all_masks_tutorial, level_str_medium1, level_str_medium2, level_str_medium3, level_str_hard1, level_str_hard2]