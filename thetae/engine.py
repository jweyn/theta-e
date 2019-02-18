#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Main engine for the theta-e system.

Step 0: check if the user has requested a utility operation, such as filling out historical data
Step 1: check the database; if database has no tables for the stid create the tables
Step 2: if applicable, run init for site: retrieves historical
Step 3: retrieve forecast data; save to database
Step 4: retrieve verification data; save to database
Step 5: run any calculation services, such as calculations for verification scores
Step 6: run plotting scripts, theta-e website scripts
"""

import sys
import os
import thetae
from thetae.util import get_object, get_config
from builtins import str
import warnings


service_groups = list(thetae.all_service_groups)


def main(args):
    """
    Main engine process.
    """
    global service_groups

    # Get the config file.
    config = get_config(args.config)
    if config['suppress_warnings']:
        warnings.filterwarnings('ignore')

    # Create the site_data archive directory, if necessary.
    site_directory = '%s/site_data' % config['THETAE_ROOT']
    if not(os.path.isdir(site_directory)):
        os.makedirs(site_directory)

    # Check for output suppression or only output options
    global service_groups
    if args.no_output:
        service_groups.remove('output_services')
        print('thetae.engine: suppressing output')
    if args.output_only:
        service_groups = ['output_services']
        print('thetae.engine: doing output only')

    # Step 1: check the database initialization
    print('thetae.engine: running database initialization checks')
    add_sites = thetae.db.init(config)

    # Check for backfill-historical sites
    if args.b_stid is not None:
        print('thetae.engine: running backfill of historical data')
        if len(args.b_stid) == 0:
            print('thetae.engine: all sites selected')
            sites = config['Stations'].keys()
        else:
            sites = args.b_stid
        for stid in sites:
            historical(config, stid)
        sys.exit(0)

    # Check for database resets
    if args.r_stid is not None:
        print('thetae.engine: performing database reset')
        if len(args.r_stid) == 0:
            print('thetae.engine: error: no sites selected!')
            sys.exit(1)
        for stid in args.r_stid:
            thetae.db.remove(config, stid)
        sys.exit(0)

    # Step 2: for each site in add_sites above, run historical data
    for stid in add_sites:
        historical(config, stid)

    # Steps 3-6: run services!
    for service_group in config['Engine']['Services'].keys():
        # Make sure we have defined a group to do what this asks
        if service_group not in service_groups:
            print('thetae.engine warning: doing nothing for services in %s' % service_group)
            continue
        for service in config['Engine']['Services'][service_group]:
            # Execute the service
            try:
                get_object(service).main(config)
            except BaseException as e:
                print('thetae.engine warning: failed to run service %s' % service)
                print("*** Reason: '%s'" % str(e))
                if config['traceback']:
                    raise


def historical(config, stid):
    """
    Run services if they have a 'historical' attribute.
    """
    global service_groups

    for service_group in config['Engine']['Services'].keys():
        # Make sure we have defined a group to do what this asks
        if service_group not in service_groups:
            print('thetae.engine warning: doing nothing for services in %s' % service_group)
            continue
        for service in config['Engine']['Services'][service_group]:
            # Execute the service.
            try:
                get_object(service).historical(config, stid)
            except AttributeError:
                if config['debug'] > 9:
                    print("thetae.engine warning: no 'historical' attribute for service %s" % service)
                continue
            except BaseException as e:
                print('thetae.engine warning: failed to run historical for service %s' % service)
                print("*** Reason: '%s'" % str(e))
                if config['traceback']:
                    raise
