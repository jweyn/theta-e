#
# Copyright (c) 2017-18 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve forecast data from a locally-run MOS-X model (https://github.com/jweyn/MOS-X). The MOS-X model must be
configured to export json files in their default file format.
"""

from thetae import Forecast
from datetime import datetime
import pandas as pd
import json

default_model_name = 'MOS-X'


def get_mosx_forecast(stid, mosx_dir, forecast_date):
    # Retrieve data
    mosx_file = '%s/MOSX_%s_%s' % (mosx_dir, stid.upper(), datetime.strftime(forecast_date, '%Y%m%d'))
    data = json.load(mosx_file)

    # Create a Forecast object and add daily values
    forecast = Forecast(stid, default_model_name, forecast_date)
    forecast.daily.setValues(data['daily']['high'], data['daily']['low'], data['daily']['wind'],
                             data['daily']['precip'])

    # Set the hourly data if it is present. Column names are already set!
    if 'hourly' in data:
        forecast.timeseries.data = pd.DataFrame(data['hourly'])

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from MOS-X.
    """
    # Get the local directory for MOS-X files from the config
    try:
        mosx_dir = config['Models'][model]['file_dir']
    except KeyError:
        raise KeyError("mosx: no 'file_dir' parameter defined for model %s in config!" % model)

    # Get forecast
    forecast = get_mosx_forecast(stid, mosx_dir, forecast_date)

    return forecast
