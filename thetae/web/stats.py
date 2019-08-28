#
# Copyright (c) 2018 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Simple tool to upload the theta-e statistics json file to a web directory.
"""

import os
from shutil import copyfile


def main(config, stid, forecast_date):
    """
    Copy the theta-e statistics json file created by calcVerification.py
    """
    # Get the file directory and attempt to create it if it doesn't exist
    try:
        file_dir = os.path.join(config['Web']['Settings']['web_directory'],
                                config['Web']['Settings']['json_directory'])
    except KeyError:
        raise KeyError("stats error: check config Web Settings parameters")

    if not(os.path.isdir(file_dir)):
        os.makedirs(file_dir)

    stats_file = '%s/archive/theta-e-stats.json' % config['THETAE_ROOT']
    dest_file = '%s/theta-e-stats.json' % file_dir

    copyfile(stats_file, dest_file)

    return
