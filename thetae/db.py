#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Functions for interfacing with SQL databases.
"""

import sqlite3
import os
import pandas as pd
from thetae.util import (get_object, TimeSeries, Daily, Forecast, date_to_datetime, date_to_string)
from datetime import datetime, timedelta


# ==============================================================================
# Connection and utility functions
# ==============================================================================

def db_conn(config, database):
    """
    Initializes a connection to the database. We only need to check for errors in the config file here, because the
    main program will try to establish a connection before making any further progress.

    :param config:
    :param database: str: name of database
    :return: sqlite3 database connection object
    """
    db_dir = '%s/archive' % config['THETAE_ROOT']
    if config['debug'] > 9:
        print('db_conn: attempting to connect to database %s' % database)
    if not (os.path.isdir(db_dir)):
        try:
            os.makedirs(db_dir)
        except:
            print('Error: could not access database directory')
            return

    # Check that the database is defined
    if not (database in config['Databases'].keys()):
        print('Error: database not defined in config file under "Databases"')
        return
    try:
        db_name = '%s/%s' % (db_dir, config['Databases'][database]['database_name'])
        if config['debug'] > 9:
            print('db_conn: using database at %s' % db_name)
    except:
        print('Error: database name error in config file')
        return

    # Establish a connection
    try:
        conn = sqlite3.connect(db_name)
    except:
        print('Error connecting to database %s' % db_name)
        return

    return conn


def db_init(config):
    """
    Initializes new station IDs in the databases. Returns a list of all sites included in config that require historical
    data to be retrieved. Also creates a database if it does not exist.

    :param config:
    """
    for data_binding in config['DataBinding'].keys():
        # Open the database and schema
        schema_name = config['DataBinding'][data_binding]['schema']
        database = config['DataBinding'][data_binding]['database']
        schema = get_object(schema_name).schema
        conn = db_conn(config, database)
        if conn is None:
            raise IOError('Error: db_init cannot connect to database %s' % database)
        cursor = conn.cursor()

        # Iterate through stations in the config
        add_sites = []
        for stid in config['Stations'].keys():
            add_site = False
            # Find the tables in the db and requested by the schema
            schema_table_names = ['%s_%s' % (stid.upper(), key) for key in schema.keys()]
            schema_table_structures = list(schema.values())
            # Schema must have primary (datetime) key listed first
            date_keys = [schema[key][0][0] for key in schema.keys()]
            if config['debug'] > 50:
                print('db_init: Found the following tables in schema:')
                print(schema_table_names)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            sql_table_names = [table[0] for table in cursor.fetchall()]
            if config['debug'] > 50:
                print('db_init: Found the following tables in sql db:')
                print(sql_table_names)

            # For each requested table, create it if it doesn't exist
            for t in range(len(schema_table_names)):
                table = schema_table_names[t]
                if not (table in sql_table_names):
                    # Something was missing, so we need to add the site to
                    # the output list
                    add_site = True
                    # A string of all table columns and types
                    if config['debug'] > 0:
                        print('db_init: need to create table %s' % table)
                    sqltypestr = ', '.join(["%s %s" % _type for _type in schema_table_structures[t]])
                    cursor.execute("CREATE TABLE %s (%s);" % (table, sqltypestr,))
                else:
                    # Check if data in table are recent
                    if table != stid.upper() + '_CLIMO':
                        recent = timedelta(days=30)
                    else:
                        recent = timedelta(days=4 * 365.25)
                    time_now = datetime.utcnow()
                    key = date_keys[t]
                    try:
                        cursor.execute("SELECT %s FROM %s ORDER BY %s DESC LIMIT 1;" % (key, table, key))
                        last_dt = date_to_datetime(cursor.fetchone()[0])
                    except:
                        last_dt = None
                    if last_dt is None or (time_now - last_dt > recent):
                        # Old or missing data, drop table and recreate it
                        add_site = True
                        if config['debug'] > 0:
                            print('db_init: %s table missing or too old, resetting it' % table)
                        cursor.execute("DROP TABLE %s;" % table)
                        sqltypestr = ', '.join(["%s %s" % _type for _type in schema_table_structures[t]])
                        cursor.execute("CREATE TABLE %s (%s);" % (table, sqltypestr,))

            # Lastly, add the site if we need to rerun historical data
            if add_site:
                add_sites.append(stid)
            elif config['debug'] > 0:
                print('db_init: nothing to do for station %s' % stid)

        conn.close()

    return add_sites


# ==============================================================================
# General writing and reading functions for SQL-formatted data
# ==============================================================================

def _db_write(config, values, database, table, replace=True):
    """
    Writes data in values to the table. Values is a list of tuples, each with the appropriate number of elements to
    fill a row in table. IMPORTANT: the appropriate number of row elements is NOT checked; will throw a SQL error.

    :param config:
    :param values: list: list of tuples corresponding to rows of column values
    :param database: str: name of database
    :param table: str: name of table to write to
    :param replace: bool: if True, calls SQL REPLACE rather than INSERT
    :return:
    """
    # Basic sanity checks on the data
    if type(values) not in [list, tuple]:
        raise TypeError('_db_write: values must be provided as a list or tuple.')
    if len(values) == 0:
        raise ValueError('_db_write: no values to write.')
    row_len = 0
    for row in values:
        if type(row) is not tuple:
            raise TypeError('_db_write: each row of values must be a tuple.')
        if row_len == 0 or row_len == len(row):
            row_len = len(row)
        else:
            raise ValueError('_db_write: all rows of values must have the same length.')
    # Find the length of the tuple formatter for the row length
    value_formatter = ('(' + '?,' * row_len)[:-1] + ')'
    # Open a database connection and execute and commit
    conn = db_conn(config, database)
    cursor = conn.cursor()
    if replace:
        sql_cmd = 'REPLACE'
        if config['debug'] > 50:
            print('_db_write: calling SQL REPLACE to overwrite existing')
    else:
        sql_cmd = 'INSERT'
        if config['debug'] > 50:
            print('_db_write: calling SQL INSERT; will raise exception if existing')
    if config['debug'] > 9:
        print('_db_write: committing values to %s table %s' % (database, table))
    if config['debug'] > 50:
        print(values)
    cursor.executemany("%s INTO %s VALUES %s;" % (sql_cmd, table, value_formatter), values)
    conn.commit()
    conn.close()


def _db_read(config, database, table, model=None, start_date=None, end_date=None):
    """
    Return a pandas DataFrame from table in database.
    If start_date and end_date are None, then then the start is set to now and the end to 24 hours in the future. If
    start_date only is None, then it is set to 24 hours before end_date. If end_date only is None, then it is set to
    24 hours after start_date.

    :param config:
    :param database: str: name of database
    :param table: str: name of table to read from
    :param model: str: specific model to read data from
    :param start_date: datetime or str: starting date
    :param end_date: datetime or str: ending date
    :return: pandas DataFrame of requested data
    """
    # Find the dates and make strings
    start_date = date_to_datetime(start_date)
    end_date = date_to_datetime(end_date)
    if start_date is None and end_date is not None:
        start_date = end_date - timedelta(hours=24)
    elif start_date is not None and end_date is None:
        end_date = start_date + timedelta(hours=24)
    elif start_date is None and end_date is None:
        start_date = datetime.utcnow()
        end_date = start_date + timedelta(hours=24)
    start = date_to_string(start_date)
    end = date_to_string(end_date)
    if config['debug'] > 9:
        print('_db_read: getting data from %s for %s to %s' % (table, start, end))

    # Open a database connection
    conn = db_conn(config, database)
    cursor = conn.cursor()

    # Fetch the data
    if model is None:
        sql_line = """SELECT * FROM %s WHERE DATETIME>=? AND DATETIME<=?
                       ORDER BY DATETIME ASC;""" % table
        cursor.execute(sql_line, (start, end))
    else:
        sql_line = """SELECT * FROM %s WHERE DATETIME>=? AND DATETIME<=?
                       AND MODEL=? ORDER BY DATETIME ASC""" % table
        cursor.execute(sql_line, (start, end, model.upper()))
    values = cursor.fetchall()
    if config['debug'] > 50:
        print('_db_read: fetched the following values')
        print(values)

    # Check that we have data
    if len(values) == 0:
        print('_db_read: warning: no valid data found, returning None')
        return

    # Get column names
    cursor.execute("PRAGMA table_info(%s);" % table)
    columns = [c[1].upper() for c in cursor.fetchall()]
    if config['debug'] > 50:
        print('_db_read: fetched the following column names')
        print(columns)
    conn.close()  # Done with db

    # Convert to DataFrame and create TimeSeries
    data = pd.DataFrame(values)
    data.columns = columns
    # If model was given, then take it out
    if model is not None:
        data = data.drop('MODEL', axis=1)

    return data


# ==============================================================================
# Writing functions for Forecast, TimeSeries, and Daily objects
# ==============================================================================

def db_writeTimeSeries(config, timeseries, data_binding, table_type):
    """
    Writes a TimeSeries object or list of TimeSeries objects to the specified data_binding and table. table_type must
    be 'obs', 'verif', 'climo', 'hourly_forecast', or 'daily_forecast', or something defined in the schema of
    data_binding as %(stid)_%(table_type).upper().
    The structure of the timeseries pandas databases should match the schema specified in the data_binding.

    :param config:
    :param timeseries: TimeSeries:
    :param data_binding: str: name of database binding to write to
    :param table_type: str: type of table
    :return:
    """
    def hourly_to_row(hourly, model, columns):
        """
        Converts an hourly timeseries to sql rows
        """
        if config['debug'] > 50:
            print('db_writeTimeSeries: converting timseries data to SQL rows')
        series = []
        hourly.columns = [c.upper() for c in hourly.columns]
        columns = [c.upper() for c in columns]
        for index, pdrow in hourly.iterrows():
            datestr = date_to_string(pdrow['DATETIME'])
            row = []
            for column in columns:
                if column == 'DATETIME':
                    row.append(datestr)
                elif column == 'MODEL':
                    row.append(model)
                elif column != 'PRIMARY KEY':
                    try:
                        row.append(pdrow[column])
                    except:
                        row.append(None)
            series.append(tuple(row))
        return series

    # Get the database and the names of columns in the schema
    database = config['DataBinding'][data_binding]['database']
    schema_name = config['DataBinding'][data_binding]['schema']
    schema = get_object(schema_name).schema
    columns = [c[0] for c in schema[table_type.upper()]]
    if config['debug'] > 50:
        print('db_writeTimeSeries: converting hourly data to columns and values as follows')
        print(columns)

    # Format data to pass to _db_write
    if type(timeseries) is list:
        hourly_sql = []
        stid = timeseries[0].stid
        for ts in timeseries:
            if stid != ts.stid:
                raise ValueError('db_writeTimeSeries error: all forecasts in list must have the same station id.')
            # Datetime must be derived from pandas dataframe of timeseries
            series = hourly_to_row(ts.data, ts.model, columns)
            if config['debug'] > 50:
                print(series)
            # Add the series (all lists)
            hourly_sql += series
    else:
        stid = timeseries.stid
        series = hourly_to_row(timeseries.data, timeseries.model, columns)
        if config['debug'] > 50:
            print(series)
        hourly_sql = series

    # Write to the database
    table = '%s_%s' % (stid.upper(), table_type.upper())
    if config['debug'] > 9:
        print('db_writeTimeSeries: writing data to table %s' % table)
    _db_write(config, hourly_sql, database, table)


def db_writeDaily(config, daily, data_binding, table_type):
    """
    Writes a Daily object or list of Daily objects to the specified data_binding and table. table_type must be 'obs',
    'verif', 'climo', 'hourly_forecast', or 'daily_forecast', or something defined in the schema of data_binding as
    %(stid)_%(table_type).upper().

    :param config:
    :param daily: Daily:
    :param data_binding: str: name of database binding to write to
    :param table_type: str: type of table
    :return:
    """
    def daily_to_row(daily, datestr, model, columns):
        """
        Converts a Daily object to a sql row
        """
        row = []
        for column in columns:
            if column.upper() == 'DATETIME':
                row.append(datestr)
            elif column.upper() == 'MODEL':
                row.append(model)
            elif column.upper() != 'PRIMARY KEY':
                row.append(getattr(daily, column, None))
        return tuple(row)

    # Get the database and the names of columns in the schema
    database = config['DataBinding'][data_binding]['database']
    schema_name = config['DataBinding'][data_binding]['schema']
    schema = get_object(schema_name).schema
    columns = [c[0] for c in schema[table_type.upper()]]
    if config['debug'] > 50:
        print('db_writeDaily: converting hourly data to columns and values as follows')
        print(columns)

    # Format data to pass to _db_write
    daily_sql = []
    if type(daily) is list:
        stid = daily[0].stid
        for d in daily:
            if stid != d.stid:
                raise ValueError('db_writeDaily error: all forecasts in list must have the same station id.')
            datestr = date_to_string(d.date)
            row = daily_to_row(d, datestr, d.model, columns)
            if config['debug'] > 50:
                print(row)
            daily_sql.append(row)
    else:
        stid = daily.stid
        datestr = date_to_string(daily.date)
        row = daily_to_row(daily, datestr, daily.model, columns)
        if config['debug'] > 50:
            print(row)
        daily_sql.append(row)

    # Write to the database
    table = '%s_%s' % (stid.upper(), table_type.upper())
    if config['debug'] > 9:
        print('db_writeDaily: writing data to table %s' % table)
    _db_write(config, daily_sql, database, table)


def db_writeForecast(config, forecast):
    """
    Function to write a Forecast object or list of Forecast objects to the main theta-e database.

    :param config:
    :param forecast: Forecast:
    :return:
    """
    # Set the default database configuration
    data_binding = 'forecast'
    if config['debug'] > 9:
        print("db_writeForecast: writing forecast to '%s' data binding" % data_binding)

    # The daily forecast part
    table_type = 'DAILY_FORECAST'
    if type(forecast) is list:
        daily = [f.daily for f in forecast]
    else:
        daily = forecast.daily
    db_writeDaily(config, daily, data_binding, table_type)

    # The timeseries forecast part
    table_type = 'HOURLY_FORECAST'
    if type(forecast) is list:
        timeseries = [f.timeseries for f in forecast]
    else:
        timeseries = forecast.timeseries
    db_writeTimeSeries(config, timeseries, data_binding, table_type)


# ==============================================================================
# Reading functions for Forecast, TimeSeries, and Daily objects
# ==============================================================================

def db_readTimeSeries(config, stid, data_binding, table_type, model=None, start_date=None, end_date=None):
    """
    Read a TimeSeries from a specified data_binding at a certain station id and of a given table type. table_type must
    be 'obs', 'hourly_forecast', or something defined in the schema of data_binding as %(stid)_%(table_type).upper().
    Model should be provided unless retrieving from obs.
    If start_date and end_date are None, then then the start is set to now and the end to 24 hours in the future. If
    start_date only is None, then it is set to 24 hours before end_date. If end_date only is None, then it is set to
    24 hours after start_date.

    :param config:
    :param stid: str: station ID
    :param data_binding: str: name of database binding to write to
    :param table_type: str: type of table
    :param model: str: model name
    :param start_date: datetime or str: starting date
    :param end_date: datetime or str: ending date
    :return: TimeSeries of requested data
    """
    # Get the database and table names
    database = config['DataBinding'][data_binding]['database']
    table = '%s_%s' % (stid.upper(), table_type.upper())

    # Get data from _db_read
    data = _db_read(config, database, table, start_date=start_date, end_date=end_date, model=model)

    # Check that we have data
    if data is None:
        raise ValueError('db_readTimeSeries error: no data retrieved.')

    # Generate TimeSeries object
    timeseries = TimeSeries(stid)
    timeseries.data = data
    if model is not None:
        timeseries.model = model

    return timeseries


def db_readDaily(config, stid, data_binding, table_type, model=None, start_date=None, end_date=None):
    """
    Read a Daily or list of Dailys from a specified data_binding at a certain station id and of a given table type.
    table_type must be 'verif', 'climo', 'daily_forecast', or something defined in the schema of data_binding as
    %(stid)_%(table_type).upper(). Model should be provided unless retrieving from verif or climo.
    If start_date and end_date are None, then then the start is set to now and the end to 24 hours in the future. If
    start_date only is None, then it is set to 24 hours before end_date. If end_date only is None, then it is set to
    24 hours after start_date.

    :param config:
    :param stid: str: station ID
    :param data_binding: str: name of database binding to write to
    :param table_type: str: type of table
    :param model: str: model name
    :param start_date: datetime or str: starting date
    :param end_date: datetime or str: ending date
    :return: Daily or list of Dailys of requested data
    """
    # Get the database and table names
    database = config['DataBinding'][data_binding]['database']
    table = '%s_%s' % (stid.upper(), table_type.upper())

    # Get data from _db_read
    data = _db_read(config, database, table, start_date=start_date, end_date=end_date, model=model)

    # Check that we have data
    if data is None:
        raise ValueError('db_readTimeSeries error: no data retrieved.')

    # Generate Daily object(s)
    daily_list = []
    for index in range(len(data.index)):
        row = data.iloc[index]
        daily = Daily(stid, row['DATETIME'])
        daily.setValues(row['HIGH'], row['LOW'], row['WIND'], row['RAIN'])
        daily.model = model
        daily_list.append(daily)
    if len(data.index) > 1:
        if config['debug'] > 9:
            print('db_readDaily: generating list of daily objects')
        return daily_list
    else:
        try:
            return daily_list[0]
        except:
            raise IndexError('db_readDaily error: no data found.')


def db_readForecast(config, stid, model, date, hour_start=6, hour_padding=6):
    """
    Return a Forecast object from the main theta-e database for a given model
    and date. This is specifically designed to return a Forecast for a single
    model and a single day.
    hour_start is the starting hour for the 24-hour forecast period.
    hour_padding is the number of hours on either side of the forecast period
    to include in the timeseries.

    :param config:
    :param stid: str: station ID
    :param model: str: model name
    :param date: datetime or str: date to retrieve
    :param hour_start: int: starting hour of the day in UTC
    :param hour_padding: int: added hours around the 24-hour TimeSeries
    :return: Forecast
    """
    # Basic sanity check for hour parameters
    if hour_start < 0 or hour_start > 23:
        raise ValueError('db_readForecast error: hour_start must be between 0 and 23.')
    if hour_padding < 0 or hour_padding > 24:
        raise ValueError('db_readForecast error: hour_padding must be between 0 and 24.')

    # Set the default database configuration; create Forecast
    data_binding = 'forecast'
    if config['debug'] > 9:
        print("db_readForecast: reading forecast from '%s' data binding" % data_binding)
    forecast = Forecast(stid, model, date)

    # The daily forecast part
    table_type = 'DAILY_FORECAST'
    daily = db_readDaily(config, stid, data_binding, table_type, model, start_date=date, end_date=date)

    # The hourly forecast part
    table_type = 'HOURLY_FORECAST'
    date = date_to_datetime(date)
    start_date = date + timedelta(hours=hour_start - hour_padding)
    end_date = date + timedelta(hours=hour_start + 24 + hour_padding)
    timeseries = db_readTimeSeries(config, stid, data_binding, table_type, model, start_date, end_date)

    # Assign and return
    forecast.timeseries = timeseries
    forecast.daily = daily
    return forecast
