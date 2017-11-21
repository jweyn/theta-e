#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Service to get verification data. The main process is used to get today and
yesterday's verification in accordance with the main engine process, while
the historical process is used in the engine historical function to produce
historical observations.
'''

from thetae.db import db_writeTimeSeries, db_writeDaily
from datetime import datetime, timedelta
from thetae.util import _get_object, _config_date_to_datetime, to_bool

def main(config):
    '''
    Main function. Runs the obs and verification for the past 24 hours.
    '''

    data_binding = 'forecast'
    
    # Figure out which day we are forecasting for: the next UTC day.
    time_now = datetime.utcnow()
    verif_date = datetime(time_now.year, time_now.month, time_now.day)
    print('getVerification: verification date %s' % verif_date)

    # Verification
    # Find the verification driver
    try:
        verif_driver = config['Verify']['Verification']['driver']
    except KeyError:
        print('getVerification error: no driver specified for Verification!')
        raise
    # Iterate over stations
    for stid in config['Stations'].keys():
        if int(config['debug']) > 9:
            print('getVerification: getting verification for station %s' % stid)
        try:
            # Verification and obs main() only need to know the stid
            verification = _get_object(verif_driver).main(config, stid)
        except BaseException as e:
            print('getVerification: failed to get verification for %s' % stid)
            print("*** Reason: '%s'" % str(e))
            continue
        # Write to the database
        try:
            if int(config['debug']) > 9:
                print('getVerification: writing verification to database')
            db_writeDaily(config, verification, data_binding, 'verif')
        except BaseException as e:
            print('getVerification: failed to write verification to database')
            print("*** Reason: '%s'" % str(e))

    # Obs
    # Find the obs driver
    try:
        obs_driver = config['Verify']['Obs']['driver']
    except KeyError:
        print('getVerification error: no driver specified for Obs!')
        raise
    # Iterate over stations
    for stid in config['Stations'].keys():
        # Get the obs
        if int(config['debug']) > 9:
            print('getVerification: getting obs for station %s' % stid)
        try:
            # Verification and obs main() only need to know the stid
            obs = _get_object(obs_driver).main(config, stid)
        except BaseException as e:
            print('getVerification: failed to get obs for %s' % stid)
            print("*** Reason: '%s'" % str(e))
            continue
        # Write to the database
        try:
            if int(config['debug']) > 9:
                print('getVerification: writing obs to database')
            db_writeTimeSeries(config, obs, data_binding, 'obs')
        except BaseException as e:
            print('getVerification: failed to write obs to database')
            print("*** Reason: '%s'" % str(e))

#    # TEST: READ SOME DATA
#    from thetae.db import db_readTimeSeries
#    timeseries = db_readTimeSeries(config, 'KSEA', data_binding, 'obs',
#                                   end_date=datetime.utcnow())
#    print(timeseries.data)

def historical(config, stid):
    '''
    Retrive historical verification (and climo!) for a stid.
    '''
    
    data_binding = 'forecast'
    
    # Figure out which days we want since config start_date
    time_now = datetime.utcnow()
    try:
        start_date = _config_date_to_datetime(config['Stations'][stid]['start_date'])
    except:
        print('getVerification warning: cannot get start_date in config for ' +
              'station %s, setting to -30 days' % stid)
        start_date = (datetime(time_now.year, time_now.month, time_now.day) -
                      timedelta(days=30))
    print('getVerification: getting historical data for %s starting %s' %
          (stid, start_date))

    # Verification
    # Find the verification driver
    try:
        verif_driver = config['Verify']['Verification']['driver']
    except KeyError:
        print('getVerification error: no driver specified for Verification!')
        raise
    # Get verification
    if int(config['debug']) > 9:
        print('getVerification: getting historical verification')
    try:
        # Verification and obs historical() need config, stid, start_date
        verification = _get_object(verif_driver).historical(config, stid, start_date)
    except BaseException as e:
        print('getVerification: failed to get historical verification for %s' % stid)
        print("*** Reason: '%s'" % str(e))
    # Write to the database
    try:
        if int(config['debug']) > 9:
            print('getVerification: writing historical verification to database')
        db_writeDaily(config, verification, data_binding, 'verif')
    except BaseException as e:
        print('getVerification: failed to write historical verification to database')
        print("*** Reason: '%s'" % str(e))

    # Obs
    # Find the obs driver
    try:
        obs_driver = config['Verify']['Obs']['driver']
    except KeyError:
        print('getVerification error: no driver specified for Obs!')
        raise
    # Get obs
    if int(config['debug']) > 9:
        print('getVerification: getting historical obs')
    try:
        # Verification and obs historical() need config, stid, start_date
        obs = _get_object(obs_driver).historical(config, stid, start_date)
    except BaseException as e:
        print('getVerification: failed to get historical obs for %s' % stid)
        print("*** Reason: '%s'" % str(e))
    # Write to the database
    try:
        if int(config['debug']) > 9:
            print('getVerification: writing historical obs to database')
        db_writeTimeSeries(config, obs, data_binding, 'obs')
    except BaseException as e:
        print('getVerification: failed to write historical obs to database')
        print("*** Reason: '%s'" % str(e))

    # Climo
    # Find the obs driver
    try:
        climo_driver = config['Verify']['Climo']['driver']
    except KeyError:
        print('getVerification error: no driver specified for Climo!')
        raise
    # Get obs
    if int(config['debug']) > 9:
        print('getVerification: getting historical climatology')
    try:
        # Verification and obs historical() need config, stid, start_date
        climo = _get_object(climo_driver).historical(config, stid)
    except BaseException as e:
        print('getVerification: failed to get climo for %s' % stid)
        print("*** Reason: '%s'" % str(e))
        return
    # Write to the database
    try:
        if int(config['debug']) > 9:
            print('getVerification: writing climo to database')
        db_writeDaily(config, climo, data_binding, 'climo')
    except BaseException as e:
        print('getVerification: failed to write climo to database')
        print("*** Reason: '%s'" % str(e))
    
    return
