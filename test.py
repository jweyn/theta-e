#!/usr/bin/env python2
#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.

"""
Instead of launching the main engine, this file runs tests to verify the
working condition of the scripts.
"""

import sys
from optparse import OptionParser

# Import the main engine
import thetae
import thetae.engine


# ==============================================================================
# Parse the input arguments
# ==============================================================================

def parseArgs():
    """
    Parse input arguments.
    """

    parser = OptionParser()
    parser.add_option("-n", "--no-output", action="store_true", dest="no_output",
                      help="Suppress all plot and web output")
    parser.add_option("-v", "--version", action="store_true", dest="version",
                      help="Display version number then exit")
    (options, args) = parser.parse_args()

    if options.version:
        print(thetae.__version__)
        sys.exit(0)

    if len(args) < 1:
        print("Missing argument(s).\n")
        print(parser.parse_args(["--help"]))
        sys.exit(1)

    return options, args


options, args = parseArgs()

# ==============================================================================
# Run tests
# ==============================================================================
