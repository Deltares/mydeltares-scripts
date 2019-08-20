#!/usr/bin/env python
import json
import logging
import os
import re
import sys
import time
from logging.handlers import RotatingFileHandler

import configparser
import requests
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

ACCESS_TOKEN_PATH = "/o/oauth2/token"
API_PATH = "/api/jsonws/invoke"
SCRIPT_PATH = os.path.dirname(os.path.realpath(sys.argv[0]))

# define global variables
client_id = None
client_secret = None
# scope = None
url = None
log_file = None
log_level = 'DEBUG'
log_maxsize = 10000000  # 10mb
# define cache variables
access_token = None
expiry_time = 0
last_line = None

apache_logfile = None
apache_logfile_name = None
apache_logfile_handle = None

sleep_time = 0.1  # sleep in between polling for a new file when handling a logrotate
reconnect_sleep_time = 2
retry_sleep_time = 1
max_attempts = 5

current_milli_time = lambda: int(round(time.time() * 1000))

# remote_host, remote_user, request_method, request_uri, time_stamp, id?
# 136.231.52.51 - - [03/Feb/2016:15:33:00 +0100] "OPTIONS /repos/delft3d/trunk HTTP/1.1" 401 381 "-" "SVN/1.8.8 (x86_64-pc-linux-gnu) serf/1.3.3"
lp = re.compile(
    r'(?P<remote_host>[^\s]+)\s-\s(?P<remote_user>[^\s]+)\s\[(?P<time_stamp>[^\]]+)\]\s"(?P<request_method>[^\s]+)\s(?P<request_uri>[^\s]+)')


def init_ini_file():
    ini_file = SCRIPT_PATH + '/svnlogger.ini'
    if not os.path.isfile(ini_file):
        raise OSError("INI file %s does not exit 'svnlogger.ini'" % ini_file)

    try:
        config = configparser.ConfigParser()
        config.read(ini_file)

        # define global variables
        global client_id
        global client_secret
        global url
        global log_file
        global log_level
        global log_maxsize

        global apache_logfile
        global apache_logfile_name
        global skip_users
        global skip_methods

        url = config.get('general', 'url')
        client_id = config.get('general', 'client_id')
        client_secret = config.get('general', 'client_secret')
        # scope = config.get('general', 'scope')
        log_file = config.get('general', 'log_file')
        log_level = config.get('general', 'log_level')
        log_max_mb = config.get('general', 'log_max_mb')
        if log_max_mb:
            log_maxsize = int(log_max_mb) * 1000000

        # location of svn logs
        apache_logfile = config.get('general', 'apache_logfile')
        apache_logfile_name = os.path.basename(apache_logfile)

        log_dir = os.path.dirname(log_file)
        if len(log_dir) == 0:
            log_name = os.path.basename(log_file)
            log_file = os.path.join(SCRIPT_PATH, log_name)

        skip_string = config.get('general', 'skip_users')
        if (len(skip_string) > 0):
            skip_users = skip_string.split(',')
        else:
            skip_users = []

        skip_string = config.get('general', 'skip_methods')
        if (len(skip_string) > 0):
            skip_methods = skip_string.split(',')
        else:
            skip_methods = ['GET']

    except configparser.NoOptionError:
        e = sys.exc_info()[1]
        print("Error reading ini file 'svnlogger.ini': %s" % e)
        return False

    return True


def init_logging():
    log_dir = os.path.dirname(log_file)

    if len(log_dir) > 0 and not os.path.isdir(log_dir):
        os.mkdir(log_dir)

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=log_level, datefmt='%Y/%m/%d %H:%M:%S')
    global logger
    logger = logging.getLogger("svnlogger")
    handler = logging.handlers.RotatingFileHandler(filename=log_file, maxBytes=log_maxsize, backupCount=5, delay=0)
    handler.setLevel(log_level)
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s',datefmt='%Y/%m/%d %H:%M:%S'))
    logger.addHandler(handler)


def check_variables():
    if apache_logfile is None:
        logger.error("No apache_log_file defined")
        return False

    pemfile = os.path.realpath('oss.deltares.nl-chain.pem')
    if os.path.exists('oss.deltares.nl-chain.pem'):
        logger.info("Using certificate file {0}".format(pemfile))
    else:
        logger.error("Could not fine certificate file {0}".format(pemfile))
        return False

    return True


def open_file_at(logfile, lastline):
    # ideally read up until just after the last known line, for now...
    f = open(logfile, 'r')
    # for now, just seek until the end of the file
    for line in f.readlines():
        if line == lastline:
            print('found last line')
            return f
    # apparently last line wasn't found, so this file must only contain new lines, reopening at the start
    print(f.tell())
    f.seek(0, os.SEEK_SET)
    print(f.tell())
    return f


def call_rest_api(method, user, host, uri):
    logger.debug("Calling REST API")

    dump = None
    try:
        json_request = {'requestMethod': method, 'remoteHost': host, 'remoteUser': user, 'requestUri': uri}
        json_data = {"/subversion.repositorylog/add-repository-log": json_request}
        # write svn logging info
        dump = json.dumps(json_data)
        response = requests.post(url + API_PATH,
                                 data=dump,
                                 headers={'Authorization': 'Bearer ' + str(access_token),
                                          'Content-Type': 'application/json'},
                                 verify=False)
# turned off   verify='oss.deltares.nl-chain.pem'
        response.raise_for_status()
        logging.info("Successfully uploaded repository log " + dump)
        return True
    except:
        e = sys.exc_info()[1]
        logger.error("Error uploading svn log %(log)s: %(error)s" % {'log': dump, 'error': e})
        return False


def get_access_token():
    logger.debug("Retrieving access token")

    global access_token
    global expiry_time

    # Get a new access token
    try:
        response = requests.post(url + ACCESS_TOKEN_PATH,
                                 data={'grant_type': 'client_credentials',
                                       'client_id': client_id, 'client_secret': client_secret},
                                 headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                 verify=False)
        # turned off verify='oss.deltares.nl-chain.pem'
        response.raise_for_status()
        body = response.json()
        exp_millis = int(body['expires_in'])*1000
        expiry_time = exp_millis + current_milli_time()
        access_token = body['access_token']
        if access_token is None:
            logger.error("No access token returned!")
            return
        logger.info("Successfully retrieved token " + str(access_token) + " expires in: " + str(exp_millis) + " millis")
    except:
        access_token = None
        e = sys.exc_info()[1]
        logger.error("Error retrieving access token: %s" % e)


def read_cache():
    ini_file = SCRIPT_PATH + '/cache.ini'

    config = configparser.ConfigParser()
    config.read(ini_file)

    global last_line
    last_line = config.get('cache', 'test.log', fallback=None)

    logger.info('last line is: "%s"' % last_line)


def write_cache():
    ini_file = SCRIPT_PATH + '/cache.ini'

    config = configparser.ConfigParser()
    config.add_section('cache')
    config.set('cache', 'test.log', last_line)
    with open(ini_file, 'w') as config_file:
        config.write(config_file)


def check_request(method, user):
    # do not process request if performed by following methods
    for m in skip_methods:
        if m == method:
            return False

    # do not process request if performed by following users
    for u in skip_users:
        if u == user:
            return False

    return True


def handle_line(line):
    mo = lp.search(line)
    if mo:
        remote_host, remote_user, time_stamp, request_method, request_uri = mo.groups()

        if (check_request(request_method[:75], remote_user[:75])):
            call_rest_api(request_method[:75], remote_user[:75], remote_host[:75], request_uri[:75])


class ApacheLogFileHandler(FileSystemEventHandler):

    def on_created(self, event):
        if not os.path.basename(event.src_path).__eq__(apache_logfile_name):
            return

        global apache_logfile_handle
        logging.debug(str(event))
        apache_logfile_handle = open_file_at(apache_logfile, last_line)
        pass

    def on_deleted(self, event):
        if not os.path.basename(event.src_path).__eq__(apache_logfile_name):
            return

        logging.debug(str(event))
        apache_logfile_handle.close()
        pass

    def on_modified(self, event):
        if not os.path.basename(event.src_path).__eq__(apache_logfile_name):
            return

        global access_token
        if expiry_time < current_milli_time() or access_token is None:
            get_access_token()
            if access_token is None:
                return
        else:
            logger.debug("Using cached access toke " + access_token)

        global last_line
        logging.debug(str(event))
        for line in apache_logfile_handle.readlines():
            handle_line(line)
            last_line = line
        if last_line:
            write_cache()
        pass

    def on_moved(self, event):
        if not os.path.basename(event.src_path).__eq__(apache_logfile_name):
            return

        logging.debug(str(event))
        apache_logfile_handle.close()
        pass

    # def on_any_event(self, event):
    #     if not os.path.basename(event.src_path).__eq__(apache_logfile_name):
    #         return
    #
    #     logging.debug(str(event))
    #     pass


def _main():
    global apache_logfile_handle

    if not init_ini_file():
        print("Failed to initialize ini file!")
        return

    init_logging()
    logger.info('Starting SVN Logger')

    if not check_variables():
        return

    read_cache()

    if os.path.isfile(apache_logfile):
        apache_logfile_handle = open_file_at(apache_logfile, last_line)

    # start watching the apache log file for updates.
    event_handler = ApacheLogFileHandler()
    observer = Observer()
    watch_path = os.path.dirname(os.path.abspath(apache_logfile))
    observer.schedule(event_handler, path=watch_path, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

    logging.shutdown(logger)


if __name__ == '__main__':
    _main()
