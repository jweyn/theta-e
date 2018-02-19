#
# Copyright (c) 2018 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Module containing web output functions.

Each sub-module should have a function main() which takes in arguments of (config, model, stid, forecast_date). The
module 'all' calls all of the web modules specified in the config, and also contains a historical function to
produce any historical output.
"""

# =============================================================================
# It may no longer be necessary to do this import, based on the change to util.get_object
# =============================================================================

# import os
#
# for module in os.listdir(os.path.dirname(__file__)):
#     if module == '__init__.py' or module[-3:] != '.py':
#         continue
#     try:
#         __import__(module[:-3], locals(), globals())
#     except BaseException as e:
#         print("data_parsers __init__.py: error importing %s" % module[:-3])
#         print("*** Reason: '%s'" % str(e))
# del module
