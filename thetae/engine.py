#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Main engine for the theta-e system.

# Step 1: check the database; if database has no table for the stid or data are
#         old, reset the table
# Step 2: if applicable, run db_init for site: retrieves historical
#   We may need to write a separate script to initialize a new model
# Step 3: retrieve forecast data; save to db
# Step 4: retrieve verification data; save to db
# Step 5: run manager to calculate verification statistics; save to db
# Step 6: run plotting scripts; theta-e website scripts
'''

import thetae
from thetae.util import _get_object, getConfig, Forecast

def main(options, args):
    '''
    Main engine process.
    '''
    
    config = getConfig(args[0])

    # Step one: check the database initialization
    print('engine: running database initialization checks')
    add_sites = thetae.db.db_init(config)

    # Step two: for each site in add_sites above, run historical data
    for stid in add_sites:
        historical(config, stid)

    # Step three/four: retrieve the forecast/verification data
    for service_group in config['Engine']['Services'].keys():
        # Make sure we have defined a group to do what this asks
        if service_group not in thetae.all_service_groups:
            print('engine: Warning: doing nothing for services in %s'
                  % service_group)
            continue
        for service in config['Engine']['Services'][service_group]:
            # Execute the service
            _get_object(service).main(config)


def historical(config, stid):
    return
