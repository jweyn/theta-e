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

def db_conn(config, data_binding):
    '''
    Initializes a connection to the database. We only need to check for errors
    in the config file here, because the main program will try to establish
    a connection before making any further progress.
    '''
    db_dir = '%s/archive' % config['THETAE_ROOT']
    if int(config['debug']) > 10:
        print('db_conn: attempting to connect to database %s' % data_binding)
    if not(os.path.isdir(db_dir)):
        try:
            os.system('mkdir -p %s' % db_dir)
        except:
            print('Error: could not access database directory')
            return
    # Check that the database is defined
    if not(data_binding in config['Databases'].keys()):
        print('Error: database not defined in config file under "Databases"')
        return
    try:
        db_name = '%s/%s' % (db_dir,
                             config['Databases'][data_binding]['database_name'])
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
    included in config that require historical data to be retrieved.
    '''
    # Find the schema
    from thetae.util import _get_object
    from datetime import datetime, timedelta
    for data_binding in config['DataBinding'].keys():
        # Open the database and schema
        schema_name = config['DataBinding'][data_binding]['schema']
        schema = _get_object(schema_name).schema
        conn = db_conn(config, data_binding)
        cursor = conn.cursor()
        # Iterate through stations in the config
        add_sites = []
        for stid in config['Stations'].keys():
            add_site = False
            # Find the tables in the db and requested by the schema
            schema_table_names = [stid.upper()+key for key in schema.keys()]
            schema_table_structures = list(schema.values())
            primary_keys = [schema[key][0][0] for key in schema.keys()]
            if int(config['debug']) > 50:
                print('db_init: Found the following tables in schema:')
                print(schema_table_names)
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            sql_table_names = [table[0][0] for table in cursor.fetchall()]
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
                    sqltypestr = ', '.join(["`%s` %s" % _type for _type in
                                            schema_table_structures[t]])
                    cursor.execute("CREATE TABLE ? (?);",
                                   (table, sqltypestr, ))
                elif table != stid.upper()+'_CLIMO': # don't check CLIMO table
                    # Check if data in table are recent
                    time_now = datetime.utcnow()
                    # Schema must have primary (datetime) key listed first
                    key = primary_keys[t]
                    cursor.execute("SELECT ? FROM ? ORDER BY ? DESC LIMIT 1;",
                                   (key, table, key))
                    last_dt = datetime.strptime(cursor.fetchone()[0],
                                                '%Y-%m-%d %H:%M')
                    if time_now - last_dt > timedelta(days=30):
                        # Old data, drop table and recreate it
                        add_site = True
                        if int(config['debug']) > 0:
                            print('db_init: %s table too old, resetting it' % table)
                        cursor.execute("DROP TABLE ?;", (table))
                        sqltypestr = ', '.join(["`%s` %s" % _type for _type in
                                                schema_table_structures[t]])
                        cursor.execute("CREATE TABLE ? (?);",
                            (table, sqltypestr, ))
            # Lastly, add the site if we need to rerun historical data
            if add_site:
                add_sites.append(stid)
    return add_sites



