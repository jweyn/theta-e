#
# Copyright (c) 2017-18 Jonathan Weyn & Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve GEFS MOS data (ensemble means)

Daily: high, low, precip (no wind speed)
Hourly: none

GEFS MOS does not account for the 06-06 UTC time frame. Ensemble values are saved to 'ensemble_file' with the util
function write_ensemble_daily.
"""

import re
from thetae import Forecast, Daily
from thetae.util import write_ensemble_daily
from datetime import datetime, timedelta
import numpy as np
import requests
from bs4 import BeautifulSoup

default_model_name = 'GEFS MOS'


def qpf_interpreter(qpf):
    """
    Interprets a QPF value average estimates

    :param qpf: q24 value from MOS
    :return: new_p: average estimated precip
    """
    translator = {
        0: 0.0,
        1: 0.05,
        2: 0.15,
        3: 0.35,
        4: 0.75,
        5: 1.5,
        6: 2.5
    }
    try:
        new_p = translator[qpf]
    except KeyError:
        new_p = 0.0
    return new_p


def get_gefs_mos_forecast(stid, forecast_date):
    """
    Retrieve GEFS MOS data. 

    :param stid: station ID
    :param forecast_date: datetime of day to forecast
    :return: Forecast object for high, low, precip for next day. No wind.
    """

    # Retrieve the model data
    url = 'http://www.nws.noaa.gov/cgi-bin/mos/getens.pl?sta=%s' % stid
    response = requests.get(url)
    page = response.text
    soup = BeautifulSoup(page, 'html.parser')

    # Lists for tomorrow's ensemble data
    ens_highs = []  
    ens_lows = []  
    ens_precips = []
    dailys = []

    # 22 total model runs
    pars = soup.find_all('pre')
    for ii in range(0, len(pars) - 1):  # last one is operational run... don't use that
        text = pars[ii].text.split()
        # control run
        if ii == 0:
            # get model time
            dates = text[5].split('/')
            hour = int(text[6])
            model_time = datetime(int(dates[2]), int(dates[0]), int(dates[1]), hour)
        # find all of the forecast hours (every 12 hr)
        forecast_hours_tmp = pars[ii].text.split('FHR')[1].split('    ')[0]
        forecast_hours = list(map(int, re.findall(r'\d+', forecast_hours_tmp)))
        # find all of the temperatures that match the forecast hours
        forecast_temps_tmp = pars[ii].text.split('X/N')[1].split('    ')[0]
        forecast_temps = list(map(int, re.findall(r'\d+', forecast_temps_tmp)))
        # find all of the 24 hour precips
        forecast_precip_tmp = pars[ii].text.split('Q24')[1].split('|')[1]
        forecast_precip = list(map(int, re.findall(r'\d+', forecast_precip_tmp)))[0:5]
        
        forecast_dates_utc = []
        temps = []
        
        for f, forecast_hour in enumerate(forecast_hours):
            # append forecast time, but subtract 1 hour so the 00Z time is for the correct date
            forecast_dates_utc.append((model_time + timedelta(hours=forecast_hour-1)).date())
            temps.append(forecast_temps[f])
        forecast_dates_utc = np.array(forecast_dates_utc)
        temps = np.array(temps)
        valid_dates = np.where((forecast_dates_utc == forecast_date.date()))[0]
        ens_highs.append(np.max(temps[valid_dates]))
        ens_lows.append(np.min(temps[valid_dates]))
        # the 24 hour precip for the next day is always the first value
        ens_precips.append(qpf_interpreter(forecast_precip[0]))

        # Add each member to the list of Daily objects, for writing to a file
        daily = Daily(stid, forecast_date)
        daily.model = 'GEFS MOS %d' % ii
        daily.setValues(ens_highs[-1], ens_lows[-1], None, ens_precips[-1])
        dailys.append(daily)

    # Get ensemble mean
    high_mean = np.round(np.mean(ens_highs))
    low_mean = np.round(np.mean(ens_lows))
    precip_mean = np.round(np.mean(ens_precips), 2)

    # Create ensemble mean Forecast object
    mean_forecast = Forecast(stid, default_model_name, forecast_date)
    mean_forecast.daily.setValues(high_mean, low_mean, None, precip_mean)

    return mean_forecast, dailys


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from GEFS MOS data.
    """

    # Get forecast
    mean_forecast, dailys = get_gefs_mos_forecast(stid, forecast_date)

    # Write the ensemble to a file, for the current STID
    if stid.upper() == config['current_stid'].upper():
        if config['debug'] > 50:
            print('gefs_mos: writing ensemble file for the current station, %s' % stid)
        try:
            ensemble_file = config['Models'][model]['ensemble_file']
        except KeyError:
            if config['debug'] > 9:
                print("gefs_mos warning: 'ensemble_file' not found in config; not writing ensemble values")
            ensemble_file = None
        try:
            write_ensemble_daily(config, dailys, ensemble_file)
        except BaseException as e:
            if config['debug'] > 0:
                print("gefs_mos warning: unable to write ensemble file ('%s')" % e)

    return mean_forecast
