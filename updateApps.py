#!venv/bin/python

# This script is used to fetch/update/install/start a web app
# (c) 2022, David Neiss, The Villages Woodshop


# TODO - ADD THE DELETE OPERATION FOR THE OLD ARCHIVES. HOLDING OFF FOR NOW


import os
import sh
import sys
import datetime


# Update this with your apps
apps = {
   "Education" : ("https://github.com/dneiss/vwc-education.git", "main")
}


# Note that for all sh invocations below, if command returns
# an error, sh will check and emit stdout, stderr, and dump a backtrack for 
# exception.

appsFullPathDir = "/var/www/fd"
isDevServer     = False
isProdServer    = False
delArchivesOlderThanDays = 180


# List all file names to recursively delete out of the app directory
filesToDelete = [".DS_Store"]


# TBD Add command line options for which app and which version to select
isDevServer = True


if isDevServer and isProdServer:
   print("ERROR, we must be configuring either a dev or prod server")
   exit(-1)
if not isDevServer and not isProdServer:
   print("ERROR, we must be configuring either a dev or prod server")
   exit(-1)


updateAll = False
appsToUpdate = sys.argv[1:]
if len(appsToUpdate) == 0:
   print("Invoke as 'updateApps.py [appName]...' or 'updateApps.py ALL'")
   exit(-1)
if len(appsToUpdate) == 1:
   if appsToUpdate[0] == "ALL":
      updateAll = True
      print("Updating ALL apps")

if not updateAll:
   for appName in appsToUpdate:
      if not appName in apps:
         print(f"ERROR: You specified app name {appName} to update, but there is no configuration data in this program for that app. Skipping")


for appName,v in apps.items():
   gitRepo        = v[0]
   gitRepoVersion = v[1]

   if not updateAll:
      if not appName in appsToUpdate:
         continue 

   print(f"Updating app: {appName}")
   myAppFullPathDir = os.path.join(appsFullPathDir,appName)
   r = sh.pwd()
   origDir = r.stdout.decode().strip()


   # TBD push out a notification to the app to tell any users that app
   # is stopping and will be updated


   # Stop service before doing update
   print(f"Stopping service for {appName}")
   r = sh.sudo(["systemctl","stop",appName])


   # Create backup dir
   print(f"Creating backup dir ArchivedApps")
   archiveFullPathDir = os.path.join(appsFullPathDir, "ArchivedApps")
   r=sh.mkdir("-p", archiveFullPathDir)

   print(f"Creating backup dir ArchivedApps/{appName}")
   appArchiveFullPathDir = os.path.join(archiveFullPathDir, appName)
   r=sh.mkdir("-p", appArchiveFullPathDir)


   # Archive original app
   if os.path.exists(myAppFullPathDir):
      timeStamp = datetime.datetime.now().strftime("%m.%d.%y-%H.%M.%S.%f").strip() 
      destPath = os.path.join(appArchiveFullPathDir, appName + "-" + timeStamp)
      print(f"Archiving current app at {myAppFullPathDir} to {destPath}")
      r = sh.mv(myAppFullPathDir,destPath)

      # Delete archives older than delArchivesOlderThanDays
      r = sh.find(appArchiveFullPathDir, "-daystart", "-mindepth", 1, "-maxdepth", 1, "-iname", f"{appName}*", "-mtime", f"+{delArchivesOlderThanDays}", "-print") 
      dirsToDelete = r.stdout.decode().strip().split("\n")

      # Filter out the empty string, which we get from prev find operation if there
      # were no matching files
      dirsToDelete = [d for d in dirsToDelete if len(d) > 0]

      if len(dirsToDelete) > 0:
         for d in dirsToDelete:
            print(f"   Old archive file will be deleted: {d}")
            # TBD add the delete here. Holding of for now because rm is a bit dangerous.
            # Need to really test this first
      else:
         print(f"There were no archived apps older than {delArchivesOlderThanDays} days old to delete")
   else:
      print(f"App dir ({myAppFullPathDir}) doesn't exist, so skipped archiving it")


   # Clone repo
   print(f"Cloning git repo {gitRepo} to {myAppFullPathDir}")
   r = sh.git.clone(gitRepo,myAppFullPathDir)


   # Checkout specific version of code
   r = sh.cd(myAppFullPathDir)
   print(f"Running git checkout for version {gitRepoVersion}")
   r = sh.git.checkout(gitRepoVersion)


   # Recursive remove any of these specified files
   for fileName in filesToDelete:
      print(f"Removing {fileName} files from {myAppFullPathDir}")
      # for some reason "rm -r" wasnt doing recursion
      r = sh.find(".","-name",fileName,"-delete")


   # Create venv 
   print(f"Creating a venv in {myAppFullPathDir}")
   r = sh.python3("-m","venv","venv")


   # Upgrade pip
   print(f"Upgrading the venv pip to latest...")
   pathToAppsPython = os.path.join(myAppFullPathDir,"venv/bin/python")
   r = os.system(f"{pathToAppsPython} -m pip install --upgrade pip")


   # Activate venv and then pip install required packages
   print(f"Pip installing into venv the required packages...")
   r = os.system(f"cd {myAppFullPathDir}; . venv/bin/activate; pip install -r requirements.txt;")

   r = sh.cd(origDir)


   # Copy in the appropriate env file and minimized its access due to secrets in file
   if isDevServer:
      print(f"Copying over the DEVELOPMENT env config file to {myAppFullPathDir}")
      sourceFile = "env.dev"
      destFile = ".env"
   elif isProdServer:
      print(f"Copying over the PRODUCTION env config file to {myAppFullPathDir}")
      sourceFile = "env.prod"
      destFile = ".env"
   else:
      print(f"ERROR, must be either DEV or PROD")
      exit(-1)
   dst = os.path.join(myAppFullPathDir,destFile)
   r = sh.cp(sourceFile,dst)
   sh.chmod("go-rwx",dst)


   # Now start/enable/status for web app service
   print(f"Start service for {appName}")
   r = sh.sudo(["systemctl","start",appName])
   print(f"Enable service for {appName}")
   r = sh.sudo(["systemctl","enable",appName])
   print(f"Check service status for {appName}")
   r = sh.sudo(["systemctl","status","-l","--no-pager",appName])


# TBD test web access
# TBD run app provided regression test on the web interface

