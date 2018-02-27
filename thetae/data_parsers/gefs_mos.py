#
# Copyright (c) 2017-18 Jonathan Weyn & Joe Zagrodnik <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Retrieve GEFS MOS data (ensemble means)

Daily: high, low, precip (no wind speed)
Hourly: none

Does not currently store information from the individual ensemble
members but this feature could easily be added in the future.

GEFS MOS does not account for the 06-06 UTC timeframe.
"""

import re
from thetae import Forecast
from datetime import datetime, timedelta
import urllib2
import numpy as np
from bs4 import BeautifulSoup
from thetae.util import get_codes, c_to_f, mph_to_kt, wind_dir_to_deg, dewpoint_from_t_rh

def mos_qpf_interpret(qpf):
    """
    Interprets a QPF value average estimates

    :param qpf: q24 value from MOS
    :return: precip: average estimated precip
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
    new_qpf = translator[qpf]

    return new_qpf

default_model_name = 'GEFS MOS'

def get_gefs_mos_forecast(stid, forecast_date):
    """
    Retrieve GEFS MOS data. 

    :param stid: station ID
    :param forecast_date: datetime of day to forecast
    :return: Forecast object for high, low, precip for next day. No wind.
    """

    # Retrieve the model data
    url = 'http://www.nws.noaa.gov/cgi-bin/mos/getens.pl?sta=%s' % stid
    req = urllib2.Request(url) 
    response = urllib2.urlopen(req)
    page = response.read().decode('utf-8', 'ignore')
    soup = BeautifulSoup(page,'html.parser')

    # Lists for tomorrow's ensemble data
    ens_highs = []  
    ens_lows = []  
    ens_precips = []

    # 22 total model runs
    pars = soup.find_all('pre')
    for ii in range(0,len(pars)-1): # last one is operational run...don't use that
        text = pars[ii].text.split()
        # control run
        if ii == 0:
            # get model time
            dates = text[5].split('/')
            hour = int(text[6])
            modeltime = datetime(int(dates[2]),int(dates[0]),int(dates[1]),hour)
        # find all of the forecast hours (every 12 hr)
        fhrs_tmp = pars[ii].text.split('FHR')[1].split('    ')[0]
        fhrs = map(int,re.findall(r'\d+',fhrs_tmp))
        # find all of the temperatures that match the forecast hours
        ftmps_tmp = pars[ii].text.split('X/N')[1].split('    ')[0]
        ftmps = map(int,re.findall(r'\d+',ftmps_tmp))
        # find all of the 24 hour precips
        fpcp_tmp = pars[ii].text.split('Q24')[1].split('|')[1]
        fpcp = map(int,re.findall(r'\d+',fpcp_tmp))[0:5]
        
        fdates_utc = []
        temps = []
        
        for ii2,fh in enumerate(fhrs):
            # append forecast time, but subtract 1 hour so the 00Z time is for the correct date
            fdates_utc.append((modeltime+timedelta(hours=fh-1)).date())
            temps.append(ftmps[ii2]) 
        fdates_utc = np.array(fdates_utc)
        temps = np.array(temps)
        gdates = np.where((fdates_utc == forecast_date.date()))[0]
        ens_highs.append(np.max(temps[gdates]))
        ens_lows.append(np.min(temps[gdates]))
        # the 24 hour precip for the next day is always the first value
        ens_precips.append(mos_qpf_interpret(fpcp[0]))

    # get ensemble mean:
    high_mean = int(np.round(np.mean(ens_highs)))
    low_mean = int(np.round(np.mean(ens_lows)))
    precip_mean = np.around(np.mean(ens_precips),2)

    # create forecast object 
    forecast = Forecast(stid, default_model_name, forecast_date)        
    forecast.daily.high = high_mean
    forecast.daily.low = low_mean
    forecast.daily.rain = precip_mean

    return forecast


def main(config, model, stid, forecast_date):
    """
    Produce a Forecast object from GEFS MOS data.
    """

    # Get forecast
    forecast = get_gefs_mos_forecast(stid, forecast_date)

    return forecast
