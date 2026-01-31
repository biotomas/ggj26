# Level format
# # = wall, @ = player, + = player on goal, $ = crystal, * = crystal on goal, . = goal, ' ' = floor
# P = push mask, B = break mask, I = ignore mask
# rules: each level must be solvable be surrounded by walls


level_str_medium3: str = """
#     B    #####
#$######## #####
#$$$$$####    I#
# #$######@#####
#*$##.P$$  $.###
#.$#############
"""


level_str_medium2: str = """
######B    #####
######$### #####
#$$$$$$### #####
#$####$###@#####
#*   $  $  #####
#. ####### #####
########## #####
########P  #####
"""

level_str_medium1: str = """
######B    #####
######$### #####
######$### #####
######$###@#####
##...$  $  $$$$#
########## ###$#
########## ###$#
########## ###$#
########## $$$P
"""


level_str_all_masks_tutorial: str = """
########
#####P##
#.$ $@ .
##B#.$$#
##$##I.#
##$#####
##.#####
########
"""

level_str_ignore_tutorial: str = """
########
#####P##
#.$ $@ #
####.$$#
#####I.#
########
"""


level_str_push_tutorial: str = """
######
####P#
#.$ @#
######
"""

all_levels = [level_str_push_tutorial, level_str_ignore_tutorial, level_str_all_masks_tutorial, level_str_medium1, level_str_medium2, level_str_medium3]