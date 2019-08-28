#
# Copyright (c) 2019 Jonathan Weyn <jweyn@uw.edu>
#
# See the file LICENSE for your rights.
#

"""
Upload settings to a theta-e website loaded dynamically from the theta-e.conf.
"""

import os
import string

template_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'template.txt')


def main(config, stid, forecast_date):
    """
    Read the template settings file and copy a settings.php file to the web directory
    """
    # Get the file directory and attempt to create it if it doesn't exist
    try:
        file_dir = config['Web']['Settings']['web_directory']
    except KeyError:
        raise KeyError("settings error: no 'web_directory' specified in config Web Settings")

    required_options = ['page_url', 'page_path', 'json_directory', 'plot_directory']
    for opt in required_options:
        if opt not in config['Web']['Settings'].keys():
            raise KeyError("settings error: required option '%s' not specified in config Web Settings" % opt)

    if not(os.path.isdir(file_dir)):
        os.makedirs(file_dir)

    # Compile substitution parameters
    params = {k: v + '/' for k, v in config['Web']['Settings'].items()}
    params.pop('web_directory')
    params['stid'] = stid = config['current_stid']
    for k in ['timezone', 'latitude', 'longitude', 'long_name']:
        try:
            params[k] = config['Stations'][stid][k]
        except KeyError:
            raise KeyError("settings error: required station option '%s' not found for station %s" % (k, stid))
    params['models'] = str(list(config['Models'].keys()))
    params['default_model'] = config['Models'].keys()[0]
    params['bufr_models'] = str([m for m in config['Models'].keys() if 'bufr_name' in config['Models'][m].keys()])

    # Replace the template with parameters
    with open(template_file, 'r') as f:
        src = string.Template(f.read())

    result = src.substitute(**params)
    if config['debug'] > 50:
        print('settings: uploading settings: %s' % params)

    # Write out to the file
    out_file = os.path.join(file_dir, 'settings.php')
    if config['debug'] > 9:
        print('settings: writing to %s' % out_file)
    with open(out_file, 'w') as f:
        f.write(result)

    return
