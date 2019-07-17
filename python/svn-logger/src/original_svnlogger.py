#!/usr/bin/env python
import os, re, time, inotify.adapters
import pymysql as mysql
from dateutil.parser import parse

logfile = '/var/log/apache2/svn.oss.deltares.nl_access_ssl.log'
status_file = '/opt/subversion/logger/test.log'
lastline = None
sleep_time = 0.1 # sleep in between polling for a new file when handling a logrotate
reconnect_sleep_time = 2
retry_sleep_time = 1
max_attempts = 5

db_host = '136.231.52.57'
db_name = 'apachelogcache'
db_username = 'xxxx'
db_password = 'xxxx'
db_charset = 'latin1' # ugh
test_query = 'SELECT 1' # simple query to test connection to db
insert_query = 'INSERT INTO oss_svn (id, time_stamp, request_method, remote_user, remote_host, request_uri) VALUES (%s, %s, %s, %s, %s, %s)'

conn = None
cur = None

# remote_host, remote_user, request_method, request_uri, time_stamp, id?
# 136.231.52.51 - - [03/Feb/2016:15:33:00 +0100] "OPTIONS /repos/delft3d/trunk HTTP/1.1" 401 381 "-" "SVN/1.8.8 (x86_64-pc-linux-gnu) serf/1.3.3"
lp = re.compile(r'(?P<remote_host>[^\s]+)\s-\s(?P<remote_user>[^\s]+)\s\[(?P<time_stamp>[^\]]+)\]\s"(?P<request_method>[^\s]+)\s(?P<request_uri>[^\s]+)')

def db_reconnect():
    global conn, cur # use the global variables here
    # connect/reconnect to the database
    for attempt in xrange(max_attempts):
        try:
            conn = mysql.connect(host=db_host, user=db_username, passwd=db_password, db=db_name, charset=db_charset)
            cur = conn.cursor()
            print('Connected to database server')
            return  # exit loop if connected
        except mysql.err.OperationalError as e:
            print(e)
            print('OperationalError: cannot reconnect, waiting and reattempting...')
            time.sleep(reconnect_sleep_time+attempt)
    # if we get here, something consistently went wrong
    raise Exception('Cannot reconnect to db after many attempts')

def db_attempt_query(query, parameters):
    global conn, cur # use the global variables here
    # attempt the query, on a connection issue, keep reattempting
    for attempt in xrange(max_attempts):
        try:
            cur.execute(query, parameters)
            print('Executed query on database server')
            return  # exit loop if ok
        except mysql.err.InternalError as e:
            # (1053, u'Server shutdown in progress')
            print(e)
            print('InternalError, server probably rebooting, waiting, reconnecting and reattempting...')
            time.sleep(retry_sleep_time+attempt)
            db_reconnect()
        except mysql.err.OperationalError as e:
            print(e)
            print('OperationalError: cannot execute, waiting, reconnecting and reattempting...')
            time.sleep(retry_sleep_time+attempt)
            db_reconnect()
    # if we get here, something consistently went wrong
    raise Exception('Cannot execute query on db after many attempts')

def load_status(status_file=status_file):
    if os.path.isfile(status_file):
        lastline = open(status_file, 'r').readline()
        return lastline
    else:
        return None

def save_status(lastline, status_file=status_file):
    f = open(status_file, 'w')
    f.write(lastline) # save the last line, so we know where we were

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

def handle_line(line, conn=conn, cur=cur):
    mo = lp.search(line)
    if mo:
        remote_host, remote_user, time_stamp, request_method, request_uri = mo.groups()
        time_stamp = int(time.mktime(parse(time_stamp, fuzzy=True).timetuple()))
        db_attempt_query(insert_query, ('dummy_id', time_stamp, request_method[:75], remote_user[:75], remote_host[:75], request_uri[:75]))
    # lastline = line

def _main():
    # TODO: handle an exit signal so it can run as a service
    db_reconnect()
    i = inotify.adapters.Inotify()
    i.add_watch(logfile)
    lastline = load_status()
    print('last line is: "%s"' % lastline)
    f = open_file_at(logfile, lastline)

    try:
        for event in i.event_gen():
            if event is not None:
                (header, type_names, watch_path, filename) = event
                if 'IN_MODIFY' in type_names:
                    # file was modified
                    print('file was modified')
                    for line in f.readlines():
                        handle_line(line)
                        lastline = line
                    if lastline:
                        save_status(lastline)
                elif 'IN_OPEN' in type_names:
                    print('file was opened')
                elif 'IN_ACCESS' in type_names:
                    print('file was accessed')
                elif 'IN_CLOSE_NOWRITE' in type_names:
                    print('file was closed without being written to')
                elif 'IN_MOVE_SELF' in type_names:
                    print('file was moved')
                    # so I should probably reopen it
                    print('reopening')
                    f.close()
                    # del f # no dangling resources
                    i.remove_watch(logfile)
                    # TODO: probably need to poll if the file exists
                    while not os.path.isfile(logfile):
                        time.sleep(sleep_time)
                    f = open_file_at(logfile, lastline)
                    i.add_watch(logfile)
                elif 'IN_CLOSE_WRITE' in type_names:
                    print('file was closed after being written to')
                else:
                    # TODO: error logging and don't bail
                    print(event)
                    raise Exception('An expected inotify event type occured')
    finally:
        i.remove_watch(logfile)

if __name__ == '__main__':
    _main()
