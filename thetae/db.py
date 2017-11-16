#
# Copyright (c) 2017 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

'''
Functions for interfacing with SQL databases.
'''

import sqlite3
import os
from thetae.util import _get_object
import thetae.schemas
from datetime import datetime, timedelta

def db_conn(config, database):
    '''
    Initializes a connection to the database. We only need to check for errors
    in the config file here, because the main program will try to establish
    a connection before making any further progress.
    '''
    
    db_dir = '%s/archive' % config['THETAE_ROOT']
    if int(config['debug']) > 0:
        print('db_conn: attempting to connect to database %s' % database)
    if not(os.path.isdir(db_dir)):
        try:
            os.system('mkdir -p %s' % db_dir)
        except:
            print('Error: could not access database directory')
            return

    # Check that the database is defined
    if not(database in config['Databases'].keys()):
        print('Error: database not defined in config file under "Databases"')
        return
    try:
        db_name = '%s/%s' % (db_dir,
                             config['Databases'][database]['database_name'])
        if int(config['debug']) > 0:
            print('db_conn: using database at %s' % db_name)
    except:
        print('Error: database name error in config file')
        return

    # Establish a connection
    try:
        conn = sqlite3.connect(db_name)
    except:
        print('Error connecting to database %s' % db_name)

    return conn

def db_init(config):
    '''
    Initializes new station IDs in the databases. Returns a list of all sites
    included in config that require historical data to be retrieved. Also
    creates a database if it does not exist.
    '''
    
    for data_binding in config['DataBinding'].keys():
        # Open the database and schema
        schema_name = config['DataBinding'][data_binding]['schema']
        database = config['DataBinding'][data_binding]['database']
        schema = _get_object(schema_name).schema
        conn = db_conn(config, database)
        if conn is None:
            raise IOError('Error: db_init cannot connect to database %s' %
                  database)
        cursor = conn.cursor()
        
        # Iterate through stations in the config
        add_sites = []
        for stid in config['Stations'].keys():
            add_site = False
            # Find the tables in the db and requested by the schema
            schema_table_names = [stid.upper()+key for key in schema.keys()]
            schema_table_structures = list(schema.values())
            # Schema must have primary (datetime) key listed first
            date_keys = [schema[key][0][0] for key in schema.keys()]
            if int(config['debug']) > 50:
                print('db_init: Found the following tables in schema:')
                print(schema_table_names)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            sql_table_names = [table[0] for table in cursor.fetchall()]
            if int(config['debug']) > 50:
                print('db_init: Found the following tables in sql db:')
                print(sql_table_names)
            
            # For each requested table, create it if it doesn't exist
            for t in range(len(schema_table_names)):
                table = schema_table_names[t]
                if not(table in sql_table_names):
                    # Something was missing, so we need to add the site to
                    # the output list
                    add_site = True
                    # A string of all table columns and types
                    if int(config['debug']) > 0:
                        print('db_init: need to create table %s' % table)
                    sqltypestr = ', '.join(["%s %s" % _type for _type in
                                            schema_table_structures[t]])
                    cursor.execute("CREATE TABLE %s (%s);" %
                                   (table, sqltypestr, ))
                elif table != stid.upper()+'_CLIMO': # don't check CLIMO table
                    # Check if data in table are recent
                    time_now = datetime.utcnow()
                    key = date_keys[t]
                    try:
                        cursor.execute("SELECT %s FROM %s ORDER BY %s DESC LIMIT 1;" %
                                       (key, table, key))
                        last_dt = datetime.strptime(cursor.fetchone()[0],
                                                    '%Y-%m-%d %H:%M')
                    except:
                        last_dt = None
                    if last_dt is None or (time_now - last_dt > timedelta(days=30)):
                        # Old or missing data, drop table and recreate it
                        add_site = True
                        if int(config['debug']) > 0:
                            print('db_init: %s table missing or too old, resetting it'
                                  % table)
                        cursor.execute("DROP TABLE %s;" % (table))
                        sqltypestr = ', '.join(["%s %s" % _type for _type in
                                                schema_table_structures[t]])
                        cursor.execute("CREATE TABLE %s (%s);" %
                                       (table, sqltypestr, ))

            # Lastly, add the site if we need to rerun historical data
            if add_site:
                add_sites.append(stid)
                    
        conn.close()
            
    return add_sites

def _db_write(config, values, database, table, replace=True):
    '''
    Writes data in values to the table. Values is a list of tuples, each with
    the appropriate number of elements to fill a row in table.
    '''
    
    # Check the data
    if type(values) not in [list, tuple]:
        raise TypeError('_db_write: values must be provided as a list or tuple.')
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
        if int(config['debug']) > 50:
            print('_db_write: calling SQL REPLACE to overwrite existing')
    else:
        sql_cmd = 'INSERT'
        if int(config['debug']) > 50:
            print('_db_write: calling SQL INSERT; will raise exception if existing')
    if int(config['debug']) > 9:
        print('_db_write: committing values to %s table %s' % (database,
                                                               table))
    if int(config['debug']) > 50:
        print(values)
    cursor.executemany("%s INTO %s VALUES %s;" % (sql_cmd, table, value_formatter),
                       values)
    conn.commit()
    conn.close()

def db_write(config, stid, values_dict, table_type, model=None):
    '''
    Example function to write data for the main theta-e processes. Calls
    _db_write which is a more generic function that writes pre-formatted data
    into the database. This function formats the data for appropriate pass to
    _db_write. For user-generated components, custom db_write functions must
    be created.
    table_type must be 'obs', 'verif', 'climo', 'hourly_forecast', or
    'daily_forecast'. If table_type is a forecast, then model must be given as
    one of the models in config.
    Values MUST be a dictionary with datetime objects as keys. The values of the
    dictionary may either be dictionaries of key,value pairs or a list to be
    converted directly into database values. If a key,values dictionary is
    provided, then the keys MUST match the columns in the database schema, with
    the exception of DateTime and Model, which MUST be the first two columns.
    
    In the future, this function will be deprecated.
    '''

    from datetime import datetime, timedelta

    # Retrieve the default database configuration
    data_binding = 'forecast'
    database = config['DataBinding'][data_binding]['database']
    # Find the appropriate table
    if table_type.upper() in ['OBS', 'VERIF', 'CLIMO', 'HOURLY_FORECAST',
                              'DAILY_FORECAST']:
        table = '%s_%s' % (stid.upper(), table_type.upper())
    else:
        raise ValueError("db_write: table_type must be 'obs', 'verif', 'climo', " +
                         "'hourly_forecast', or 'daily_forecast'.")
    if 'FORECAST' in table_type.upper() and type(model) is not str:
        raise ValueError('db_write: model must be provided as a string if ' +
                         ' table_type is a forecast.')
    if int(config['debug']) > 9:
        print('db_write: writing data to table %s' % table)

    # Get the names of columns in the schema
    schema_name = config['DataBinding'][data_binding]['schema']
    schema = _get_object(schema_name).schema
    columns = [c[0] for c in schema['_%s' % table_type.upper()]]
    if int(config['debug']) > 50:
        print('db_write: converting input data to columns and values as follows')
        print(columns)
    # Parse the dictionary
    date_keys = list(values_dict.keys())
    values_sql = []
    if model is None:
        model_tuple = ()
    else:
        model_tuple = (model,)
    for date in date_keys:
        datestr = datetime.strftime(date, '%Y-%m-%d %H:%M')
        if type(values_dict[date]) is list or type(values_dict[date]) is tuple:
            row = (datestr,) + model_tuple + tuple(values_dict[date])
        elif type(values_dict[date]) is dict:
            row = []
            for column in columns:
                if ((column.upper() != 'DATETIME') and
                    (column.upper() != 'PRIMARY KEY') and
                    (column.upper() != 'MODEL')):
                    try:
                        row.append(values_dict[date][column])
                    except:
                        row.append(None)
            row = (datestr,) + model_tuple + tuple(row)
        if int(config['debug']) > 50:
            print(row)
        values_sql.append(row)

    # Write to the database
    _db_write(config, values_sql, database, table)

def db_writeTimeSeries(config, timeseries, data_binding, table_type):
    '''
    Writes a TimeSeries object or list of TimeSeries objects to the specified
    data_binding and table.
    table_type must be 'obs', 'verif', 'climo', 'hourly_forecast', or
    'daily_forecast', or something defined in the schema of data_binding as
    %(stid)_%(table_type).upper().
    The structure of the timeseries pandas databases should match the schema
    specified in the data_binding.
    '''
    
    def hourly_to_row(hourly, model, columns):
        '''
        Converts an hourly timeseries to sql rows
        '''
        if int(config['debug']) > 50:
            print('db_writeTimeSeries: converting timseries data to SQL rows')
        series = []
        hourly.columns = [c.upper() for c in hourly.columns]
        columns = [c.upper() for c in columns]
        for index, pdrow in hourly.iterrows():
            datestr = pdrow['DATETIME']
            if type(datestr) is not str:
                datestr = datetime.strftime(datestr, '%Y-%m-%d %H:%M')
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
    schema = _get_object(schema_name).schema
    columns = [c[0] for c in schema['_%s' % table_type.upper()]]
    if int(config['debug']) > 50:
        print('db_writeTimeSeries: converting hourly data to columns and ' +
              'values as follows')
        print(columns)
    
    # Format data to pass to _db_write
    if type(timeseries) is list:
        hourly_sql = []
        stid = timeseries[0].stid
        for ts in timeseries:
            if stid != ts.stid:
                raise ValueError('db_writeTimeSeries error: all forecasts in ' +
                                 'list must have the same station id.')
            # Datetime must be derived from pandas dataframe of timeseries
            series = hourly_to_row(ts.data, ts.model, columns)
            if int(config['debug']) > 50:
                print(series)
            # Add the series (all lists)
            hourly_sql += series
    else:
        stid = timeseries.stid
        series = hourly_to_row(timeseries.data, timeseries.model, columns)
        if int(config['debug']) > 50:
            print(series)
        hourly_sql = series

    # Write to the database
    table = '%s_%s' % (stid.upper(), table_type)
    if int(config['debug']) > 9:
        print('db_writeTimeSeries: writing data to table %s' % table)
    _db_write(config, hourly_sql, database, table)

def db_writeDaily(config, daily, data_binding, table_type):
    '''
    Writes a Daily object or list of Daily objects to the specified
    data_binding and table.
    table_type must be 'obs', 'verif', 'climo', 'hourly_forecast', or
    'daily_forecast', or something defined in the schema of data_binding as
    %(stid)_%(table_type).upper().
    '''

    def daily_to_row(daily, datestr, model, columns):
        '''
        Converts a Daily object to a sql row
        '''
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
    schema = _get_object(schema_name).schema
    columns = [c[0] for c in schema['_%s' % table_type.upper()]]
    if int(config['debug']) > 50:
        print('db_writeDaily: converting hourly data to columns and ' +
              'values as follows')
        print(columns)

    # Format data to pass to _db_write
    daily_sql = []
    if type(daily) is list:
        stid = daily[0].stid
        for d in daily:
            if stid != d.stid:
                raise ValueError('db_writeDaily error: all forecasts in list ' +
                                 'must have the same station id.')
            datestr = datetime.strftime(d.date, '%Y-%m-%d %H:%M')
            row = daily_to_row(d, datestr, d.model, columns)
            if int(config['debug']) > 50:
                print(row)
            daily_sql.append(row)
    else:
        stid = daily.stid
        datestr = datetime.strftime(daily.date, '%Y-%m-%d %H:%M')
        row = daily_to_row(daily, datestr, daily.model, columns)
        if int(config['debug']) > 50:
            print(row)
        daily_sql.append(row)

    # Write to the database
    table = '%s_%s' % (stid.upper(), table_type)
    if int(config['debug']) > 9:
        print('db_writeDaily: writing data to table %s' % table)
    _db_write(config, daily_sql, database, table)

def db_writeForecast(config, forecast):
    '''
    Function to write a Forecast object or list of Forecast objects to the main
    theta-e database.
    '''
    
    # Set the default database configuration
    data_binding = 'forecast'
    if int(config['debug']) > 9:
        print("db_writeForecast: writing forecast to '%s' data binding"
              % data_binding)
    
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





