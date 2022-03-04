# updateWebApps.py

This script automates the updating of the dev or prod server's web apps. It does this by cloning a VWC web app into the proper directory to be served 
up by the web server and doing all necessary work to provision it and its necessary files. Before doing the update, it archives the current web app under the /var/www/fd/ArchivedApps/{appName} dir. Archived apps have a file name suffix of the time stamp when they were archived.

Invoke as `updateApps.py [appName]...` or `updateApps.py ALL` where ALL will update all configured apps.

Update the `appsConfig.py` file with all known apps.

