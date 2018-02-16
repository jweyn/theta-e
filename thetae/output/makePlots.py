#
# Copyright (c) 2017 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Service to make all plots specified in config. The main process is used to
get the next day's forecast in accordance with the main engine process.
A historical or climo process could be added to do past plots. 
"""

from datetime import datetime, timedelta
from thetae.util import get_object

def main(config):
    """
    Main function. Iterates through plotting scripts
    """

    # Figure out which day we are forecasting for: the next UTC day.
    time_now = datetime.utcnow()
    forecast_date = (datetime(time_now.year, time_now.month, time_now.day) + timedelta(days=1))
    print('makePlots: forecast date %s' % forecast_date)

    # Go through the models in config
    for plot_type in config['Plot'].keys():
        try:
            driver = config['Plot'][plot_type]['driver']
        except KeyError:
            print('MakePlots warning: driver not specified for plot type %s' % plot_type)
            continue
        print('makePlots: making plots for %s' % plot_type)

        # Make the plot from the driver at each site
        for stid in config['Stations'].keys():
            if config['debug'] > 9:
                print('makePlots: making plots for station %s' % stid)
            try:
                # Each plotting script has a function 'main' which makes a plot
                get_object(driver).main(config, stid, forecast_date)
                print('makePlots: successfully made plot %s for %s' % (plot_type, stid))
            except BaseException as e:
                print('makePlots: failed to make plot %s for %s' % (plot_type, stid))
                print("*** Reason: '%s'" % str(e))
                if config['traceback']:
                    raise
                continue
            

