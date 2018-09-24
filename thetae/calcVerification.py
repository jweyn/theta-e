#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Calculate verification scores and metrics. These are not saved to the database, but in a json file.
"""

import numpy as np
from thetae.db import readDaily
from datetime import datetime, timedelta
from thetae.util import get_object, date_to_string, last_leap_year
from collections import OrderedDict
import json


def get_forecast_stats(forecasts, verifs, day_list=None):
    """
    Returns the statistics of a forecast relative to a verification.
    """
    if day_list is not None:
        days = day_list
    else:
        days = list(forecasts.keys() & verifs.keys())
    num_days = len(days)
    stats_dict = OrderedDict()
    stats_dict['attrs'] = OrderedDict()
    stats_dict['attrs']['numDays'] = num_days
    stats_dict['attrs']['verifyingDays'] = days
    stats_dict['stats'] = OrderedDict()

    if num_days < 1:
        return stats_dict

    for var in ['high', 'low', 'wind', 'rain']:
        stats_dict['stats'][var] = OrderedDict()

        forecast_values = np.array([getattr(forecasts[day], var) for day in days], dtype=np.float)
        verif_values = np.array([getattr(verifs[day], var) for day in days], dtype=np.float)

        bias = np.nanmean(forecast_values - verif_values)
        rmse = np.nanmean(np.sqrt((forecast_values - verif_values) ** 2.))
        rmse_no_bias = np.nanmean(np.sqrt((forecast_values - bias - verif_values) ** 2.))
        stats_dict['stats'][var]['bias'] = bias
        stats_dict['stats'][var]['rmse'] = rmse
        stats_dict['stats'][var]['rmseNoBias'] = rmse_no_bias

    return stats_dict


def list_to_dict(dailys):
    """
    Returns a {date: daily} dictionary from a list of Daily objects. Converts the date to a string.
    """
    daily_dict = OrderedDict()
    for daily in dailys:
        daily_dict[date_to_string(daily.date)] = daily
    return daily_dict


def replace_nan_in_dict(d):
    for key, val in d.items():
        if isinstance(val, dict):
            replace_nan_in_dict(val)
        else:
            try:
                if np.isnan(val) or np.isinf(val):
                    d[key] = None
            except TypeError:
                pass


def main(config):
    """
    Main function. Runs the verification calculation.
    """

    data_binding = 'forecast'

    # Figure out which days we are verifying for: up to yesterday.
    time_now = datetime.utcnow() - timedelta(days=1, hours=6)
    end_date = datetime(time_now.year, time_now.month, time_now.day)
    print('calcVerification: calculating statistics through %s' % end_date)
    start_date = end_date - timedelta(days=31)

    # The directory and archive file
    db_dir = '%s/archive' % config['THETAE_ROOT']
    stats_file = '%s/theta-e-stats.json' % db_dir
    stats = OrderedDict()

    # Iterate over stations
    for stid in config['Stations'].keys():
        if config['debug'] > 9:
            print('calcVerification: calculating statistics for station %s' % stid)

        # Load verification and climo data
        if config['debug'] > 50:
            print('calcVerification: loading verification and climo data')
        verification = readDaily(config, stid, data_binding, 'verif', start_date=start_date, end_date=end_date)
        climo = []
        current_date = start_date
        while current_date <= end_date:
            climo_date = current_date.replace(year=last_leap_year())
            climo_day = readDaily(config, stid, data_binding, 'climo', start_date=climo_date, end_date=climo_date)
            climo_day.date = current_date
            climo.append(climo_day)
            current_date += timedelta(days=1)

        # Get persistence and convert to dictionaries
        persistence = OrderedDict()
        for v in verification:
            persistence[date_to_string(v.date + timedelta(days=1))] = v
        verification = list_to_dict(verification)
        climo = list_to_dict(climo)

        stats[stid] = OrderedDict()
        for model in list(config['Models'].keys()):
            if config['debug'] > 50:
                print('calcVerification: loading forecast data for %s' % model)
            try:
                forecasts = readDaily(config, stid, data_binding, 'daily_forecast', model=model,
                                      start_date=start_date+timedelta(days=1), end_date=end_date)
                forecasts = list_to_dict(forecasts)
            except ValueError:
                print('calcVerification warning: no data found for model %s at %s' % (model, stid))
                continue
            verif_days = [d for d in forecasts.keys() if (d in verification.keys() and d in climo.keys() and
                                                          d in persistence.keys())]

            # Get stats for each of the model, climo, and persistence. We do this for every model so that the skill
            # scores can be compared across different sets of available verification days for each model.
            if config['debug'] > 50:
                print('calcVerification: calculating statistics for %s' % model)
            model_stats = get_forecast_stats(forecasts, verification, day_list=verif_days)
            climo_stats = get_forecast_stats(climo, verification, day_list=verif_days)
            persist_stats = get_forecast_stats(persistence, verification, day_list=verif_days)

            # Add in the skill scores
            for var in ['high', 'low', 'wind', 'rain']:
                model_stats['stats'][var]['skillClimo'] = 1. - (model_stats['stats'][var]['rmse'] /
                                                                climo_stats['stats'][var]['rmse'])
                model_stats['stats'][var]['skillClimoNoBias'] = 1. - (model_stats['stats'][var]['rmseNoBias'] /
                                                                      climo_stats['stats'][var]['rmse'])
                model_stats['stats'][var]['skillPersist'] = 1. - (model_stats['stats'][var]['rmse'] /
                                                                  persist_stats['stats'][var]['rmse'])
                model_stats['stats'][var]['skillPersistNoBias'] = 1. - (model_stats['stats'][var]['rmseNoBias'] /
                                                                        persist_stats['stats'][var]['rmse'])

            # Remove NaN (not interpreted by json) and add to the large dictionary
            replace_nan_in_dict(model_stats)
            stats[stid][model] = model_stats

    # Write to the file

    with open(stats_file, 'w') as f:
        json.dump(stats, f)
