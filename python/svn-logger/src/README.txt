Subversion logger:

Write subversion log messages from svn.oss.deltares.nl to the liferay REST API.
Whenever a user performs a Subversion action, this is logged by subversion. The svnlogger script monitors these logs
and sends the information to a Liferay instance. On the Liferay side the Subversion-service module receives the messages
from this script and stores these in its database. These log messages are presented to the user via the activity-map
module.


Example call:

POST: http://localhost:8090/api/jsonws/invoke

	header:
	Authorization: Basic or Bearer token
	Content-Type: application/json


	body:
	{
	    "/subversion.repositorylog/add-repository-log": {	
		    "requestMethod": "PUT",
		    "remoteHost": "195.208.218.98",
		    "remoteUser": "e.de.rooij2@kpnplanet.nl",
		    "requestUri": "/repos/delftfews"
	    }
	}

configure adapter:

svnlogger.ini

url = root url to Liferay instance
client_id       = client Id configured in Oauth2 section of Liferay instance
client_secret   = client secret belonging to client Id
log_level       = logging level
log_file        = path to logfile. If only name then file is created locally
log_max_mb=5    = maximum size of logfile in MB before it rolls over
apache_logfile  = path to where the subversion access logs is located

installation:

This script needs to be deployed on the V-OSS003 (136.231.52.52) in directory: /opt/subversion/logger

startup command: /opt/subversion/logger/bin/python /opt/subversion/logger/svnlogger.py

apache_logfile location on the V-0SS003 /var/log/apache2/svn.oss.deltares.nl_access_ssl.log

This script has been tested on python 2.7.16 and 3.7.4

Required modules 2.7.16:
PyYAML	5.1.1	5.1.1
argh	0.26.2	0.26.2
certifi	2019.6.16	2019.6.16
chardet	3.0.4	3.0.4
configparser	3.7.4	3.7.4
idna	2.8	2.8
pathtools	0.1.2	0.1.2
pip	19.1.1	19.1.1
requests	2.22.0	2.22.0
setuptools	41.0.1	41.0.1
urllib3	1.25.3	1.25.3
watchdog	0.9.0	0.9.0
wheel	0.33.4	0.33.4

Required modules 3.7.4:
PyYAML	5.1.1	5.1.1
argh	0.26.2	0.26.2
certifi	2019.6.16	2019.6.16
chardet	3.0.4	3.0.4
idna	2.8	2.8
pathtools	0.1.2	0.1.2
pip	19.0.3	19.1.1
requests	2.22.0	2.22.0
setuptools	40.8.0	41.0.1
urllib3	1.25.3	1.25.3
watchdog	0.9.0	0.9.0

