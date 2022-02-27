#!venv/bin/python

# This script is used to fetch/update/install/start a web app
# (c) 2022, David Neiss, The Villages Woodshop

import os
import sh
import datetime

# TBD command line options for which app and which version to select
#select app name
#select app branchtip, sha, or tag


# TBD ADD ERROR CHECKS FOR EACH STEP AND MORE DEBUG OUTPUT

appName         = "Education"
gitRepo         = "https://github.com/dneiss/vwc-education.git"
gitRepoVersion  = "main"
appsFullPathDir = "/var/www/fd"

myAppFullPathDir = os.path.join(appsFullPathDir,appName)

# Get into working dir area
#r = sh.cd(f"/var/www/fd")
#print(r)

# Stop service before doing update
print(f"stopping service for {appName}")
r = sh.sudo(["systemctl","stop",appName])

# Create backup dir
myAppArchiveFullPathDir = os.path.join(appsFullPathDir,appName+".archived")
print(f"Creating backup dir {appName}")
r=sh.mkdir("-p",myAppArchiveFullPathDir)

# Archive original app
if os.path.exists(myAppFullPathDir):
   timeStamp = datetime.datetime.now().strftime("%m.%d.%y-%H.%M.%S.%f").strip() 
   destPath = os.path.join(myAppArchiveFullPathDir, appName + "-" + timeStamp)
   print(f"Archiving current app at {myAppFullPathDir} to {destPath}")
   r = sh.mv(myAppFullPathDir,destPath)
# TBD prune older than N archives to reduce storage
else:
   print(f"App dir ({myAppFullPathDir}) doesn't exist, so skipped archiving it")

# Clone repo
print(f"Cloning git repo {gitRepo} to {myAppFullPathDir}")
r = sh.git.clone(gitRepo,myAppFullPathDir)

# Checkout specific version of code
r = sh.cd(myAppFullPathDir)
print(f"Running git checkout for version {gitRepoVersion}")
r = sh.git.checkout(gitRepoVersion)

# Create venv 
print(f"Creating venv")
r = sh.python3("-m","venv","venv")

# Upgrade pip
print(f"Upgrading pip...")
pathToAppsPython = os.path.join(myAppFullPathDir,"venv/bin/python")
r = os.system(f"{pathToAppsPython} -m pip install --upgrade pip")
print(r)

# activate venv and then pip install required packages
print(f"Pip installing required packages...")
r = os.system(f"cd {myAppFullPathDir}; . venv/bin/activate; pip install -r requirements.txt;")

#copy in env file
#start/enable/status systemctl
#test web access

#eventually, run a regression test on software

