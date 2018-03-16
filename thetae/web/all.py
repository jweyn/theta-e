#
# Copyright (c) 2018 Jonathan Weyn + Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Service to run all web outputs specified in config. The main process is used to output the next day's data in
accordance with the main engine process. The historical function generates past data that only need run once.
"""

from datetime import datetime, timedelta
from thetae.util import get_object, config_date_to_datetime, to_bool
from builtins import str


def main(config):
    """
    Main function. Iterates through all output scripts specified in config.
    """

    # Figure out which day we are forecasting for: the next UTC day.
    time_now = datetime.utcnow()
    forecast_date = (datetime(time_now.year, time_now.month, time_now.day) + timedelta(days=1))
    if config['debug'] > 9:
        print('web.all: forecast date %s' % forecast_date)

    # Get the output types from config
    try:
        output_types = list(config['Web']['outputs'])
    except KeyError:
        print("web.all warning: no output specified by key 'outputs' in config!")
        return
    # If a config option is given to do outputs for all stations, do so
    try:
        plot_all_stations = to_bool(config['Web']['Options']['output_all_stations'])
    except:
        plot_all_stations = False
    if plot_all_stations:
        stations = config['Stations'].keys()
    else:
        stations = [config['current_stid']]

    # Do the outputs
    for output_type in output_types:
        print("web.all: producing '%s' output" % output_type)
        for stid in stations:
            if config['debug'] > 50:
                print("web.all: output '%s' for station %s" % (output_type, stid))
            try:
                # Each web script has a function 'main' which produces a specific output
                get_object('thetae.web.%s' % output_type).main(config, stid, forecast_date)
            except BaseException as e:
                print('web.all: failed to output %s for %s' % (output_type, stid))
                print("*** Reason: '%s'" % str(e))
                if config['traceback']:
                    raise
                continue


def historical(config, stid):
    """
    Function to produce historical web output, for a specific site. Iterates over web functions specified in config
    which have a 'historical' attribute, and begins at the config start_date.
    """

    print('web.all: generating historical output for station %s' % stid)

    # Figure out which days we are forecasting for since config start_date.
    time_now = datetime.utcnow()
    forecast_dates = []
    try:
        start_date = config_date_to_datetime(config['Stations'][stid]['start_date'])
    except:
        print('web.all warning: cannot get start_date in config for station %s, setting to -30 days' % stid)
        start_date = (datetime(time_now.year, time_now.month, time_now.day) - timedelta(days=30))
    date = start_date
    while date < time_now:
        forecast_dates.append(date)
        date = date + timedelta(hours=24)
    if config['debug'] > 9:
        print('web.all: historical output starting %s' % start_date)

    # Get the output types from config
    try:
        output_types = list(config['Web']['outputs'])
    except KeyError:
        print("web.all warning: no output specified by key 'outputs' in config!")
        return
    for output_type in output_types:
        print("web.all: producing '%s' output" % output_type)
        if config['debug'] > 9:
            print("web.all: output '%s' for station %s" % (output_type, stid))
        try:
            # Each output script has a function 'main' which produces a specific output
            get_object('thetae.web.%s' % output_type).historical(config, stid)
        except AttributeError:
            if config['debug'] > 9:
                print("web.all: no historical '%s' output" % output_type)
        except BaseException as e:
            print('web.all: failed to output %s for %s' % (output_type, stid))
            print("*** Reason: '%s'" % str(e))
            if config['traceback']:
                raise
            continue

    return
