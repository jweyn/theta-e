#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Module containing database schemas. Please see the default.py schema for
example database structures.
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
