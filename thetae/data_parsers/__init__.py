#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Module containing forecast data parsers.

Each sub-module should have a function main() which takes in arguments of
(config, stid, forecast_date). The main function should return a Forecast
object.
'''

# =============================================================================
# Make sure we import everything in here.
# =============================================================================

import os
for module in os.listdir(os.path.dirname(__file__)):
    if module == '__init__.py' or module[-3:] != '.py':
        continue
    __import__(module[:-3], locals(), globals())
del module
