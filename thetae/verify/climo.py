#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve climatology data from ulmo's ghcn_daily
"""

import ulmo
import numpy as np
from thetae.util import get_ghcn_stid, Daily, last_leap_year
from datetime import datetime, timedelta
from builtins import str


def get_ghcn_data(ghcn_stid):
    """
    Retrieve GHCN high, low, wind, and rain data for a station. Output is a
    dictionary with a pandas dataframe as values.
    """

    vars_used = ['TMAX', 'TMIN', 'WSF2', 'PRCP']
    ghcn_data = ulmo.ncdc.ghcn_daily.get_data(ghcn_stid, elements=vars_used, as_dataframe=True)

    # Change dataframe Indexes to DatetimeIndex
    for var in ghcn_data.keys():
        ghcn_data[var].index = ghcn_data[var].index.to_timestamp()

    return ghcn_data


def get_climo(config, stid, ghcn_stid, start_year=1980):
    """
    Get climatological values as a list of Daily objects for the station
    ghcn_stid, with a climatology starting in start_year. There is no specified
    end year because wind data are limited.
    """

    # Retrieve the data
    print('climo: fetching data for GHCN station %s' % ghcn_stid)
    ghcn = get_ghcn_data(ghcn_stid)

    # For each variable, use groupby to get yearly climo
    if config['debug'] > 9:
        print('climo: grouping data into yearly climatology')
    aggregate = {'value': np.mean}
    ghcn_yearly = {}
    if config['debug'] > 9:
        print('climo: averaging for years since %d' % start_year)
    for var, df in ghcn.items():
        # Apparently values are "object" type. Convert to floats
        df['value'] = df['value'].astype(str).astype(np.float64)
        # Remove any data older than start year
        df = df[df.index > datetime(start_year, 1, 1)]
        ghcn_yearly[var] = df.groupby([df.index.month, df.index.day]).agg(aggregate)

    # Now we have dataframes with indices (month, day). We need to use the
    # nearest leap year to avoid confusion with Feb 29
    year = last_leap_year()
    # Create a list of Dailys
    dailys = []
    if config['debug'] > 50:
        print('climo: here are the values')
    for index, row in ghcn_yearly['TMAX'].iterrows():
        date = datetime(year, index[0], index[1])
        daily = Daily(stid, date)
        # We also need to convert units! Temp from 10ths of C to F, wind from
        # 10ths of m/s to kts, rain from 10ths of mm to in.
        daily.high = ghcn_yearly['TMAX'].loc[index]['value'] / 10. * 9. / 5. + 32.
        daily.low = ghcn_yearly['TMIN'].loc[index]['value'] / 10. * 9. / 5. + 32.
        daily.wind = ghcn_yearly['WSF2'].loc[index]['value'] / 10. * 1.94384
        daily.rain = ghcn_yearly['PRCP'].loc[index]['value'] / 254.
        if config['debug'] > 50:
            print('%s %0.0f/%0.0f/%0.0f/%0.2f' % (daily.date, daily.high, daily.low, daily.wind, daily.rain))
        dailys.append(daily)

    return dailys


def historical(config, stid, start_year=1980):
    """
    Get historical climatology data
    """

    ghcn_stid = get_ghcn_stid(config, stid)

    dailys = get_climo(config, stid, ghcn_stid, start_year)

    return dailys
