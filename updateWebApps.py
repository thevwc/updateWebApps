#!venv/bin/python
"""
    This script is used to fetch/update/install/start a web app
    (c) 2022, David Neiss, The Villages Woodshop
"""

# TODO - ADD THE DELETE OPERATION FOR THE OLD ARCHIVES. HOLDING OFF FOR NOW

import sys
import os
import datetime
import logging
import sh
from appsConfig import apps
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-7s %(message)s',
                    datefmt='%m-%d-%Y %I:%M:%S %p',
                    handlers=[logging.FileHandler("updateWebApps.log", mode='a'),logging.StreamHandler(sys.stdout)])


# Logging stdout from subprocesses is a bit complicated because python's stdout is
# only shallow (forked subprocesses don't honor it) so its a bit more complicated
# and requires the use of the wurlitzer pipe redirector - see the Pypi wurlitzer
# page and its references for more info.

# to use, take your line of code that would subprocess out and add a decorator to
# it, wrap it in a run function, and run it:

# from:
#  sh.ls
# to:
#  @DeepRepipeStdErrAndStdOutToLogger
#  def run(stdOut, stdErr):
#     return sh.ls
#  run()

def DeepRepipeStdErrAndStdOutToLogger(func):
    def pipeRedir():
        from io import StringIO
        pipesStdOut = StringIO()
        pipesStdErr = StringIO()
        from wurlitzer import pipes

        # Raise level to INFO because DEBUG level resulted in spew from sh. This is
        # a hack because who knows if func is sh. There must be a better way of doing this
        oldLevel = logging.getLogger().level
        logging.getLogger().setLevel(logging.INFO)

        with pipes(stdout=pipesStdOut, stderr=pipesStdErr):
            ret = func(pipesStdOut,pipesStdErr)

        logging.getLogger().setLevel(oldLevel)

        # Note that this doesn't preserve the time order of messages sent to stdout and stderr,
        # they will all appear to have occurred at the same time. Furthermore, all stdout will proceed
        # all stderr messages. Would be better to rework the code so that this isn't the case.

        for v1 in pipesStdOut.getvalue().splitlines():
            logging.info(v1)
        for v2 in pipesStdErr.getvalue().splitlines():
            logging.error(v2)
        return ret

    return pipeRedir


def get_base_prefix_compat():
    """Get base/real prefix, or sys.prefix if there is none."""
    return getattr(sys, "base_prefix", None) or getattr(sys, "real_prefix", None) or sys.prefix

def in_virtualenv():
    """Returns True if in venv"""
    return get_base_prefix_compat() != sys.prefix

def isPython3():
    """Returns True if running under Py3"""
    return sys.version_info[0] == 3

if not isPython3():
    logging.error("ERROR - you should be running this with Python3")
    sys.exit(-1)
if not in_virtualenv():
    logging.error("ERROR - you should probably run this in its local venv, 'source venv/bin/activate'")
    sys.exit(-1)


# Note that for all sh invocations below, if command returns
# an error, sh will check and emit stdout, stderr, and dump a backtrack for
# exception.

appsFullPathDir  = "/var/www/fd"
isDevServer      = False
isProdServer     = False
delArchivesOlderThanDays = 180


# List all file names to recursively delete out of the app directory
filesToDelete = [".DS_Store"]


isDevServer = True


if isDevServer and isProdServer:
    logging.error("ERROR, we must be configuring either a dev or prod server")
    sys.exit(-1)
if not isDevServer and not isProdServer:
    logging.error("ERROR, we must be configuring either a dev or prod server")
    sys.exit(-1)


updateAll = False
appsToUpdate = sys.argv[1:]
if len(appsToUpdate) == 0:
    print("Invoke as 'updateWebApps.py [appName[:treeish]]...' or 'updateWebApps.py ALL'. Note that treeish is optional and is a SHA,branch,HEAD,or tag")
    sys.exit(-1)
if len(appsToUpdate) == 1:
    if appsToUpdate[0] == "ALL":
        updateAll = True
        logging.info("Updating ALL apps")


# Extract the optional tree-ish suffix. If found, patch up config's default
# treeish-to-checkout with it

def ExtractTreeish(appNameWithOptionalColonAndTreeishSuffix):
    """Returns (appName,treeish) extracted from param"""
    colonIndex = appNameWithOptionalColonAndTreeishSuffix.find(":")
    if colonIndex > -1:
        app_name = appNameWithOptionalColonAndTreeishSuffix[:colonIndex]
        tree_ish = appNameWithOptionalColonAndTreeishSuffix[colonIndex+1:]
    else:
        app_name = appNameWithOptionalColonAndTreeishSuffix
        tree_ish = None
    return app_name,tree_ish

for i,cmdLineAppName in enumerate(appsToUpdate):
    appName,treeish = ExtractTreeish(cmdLineAppName)
    if treeish:
        if appName in apps:
            apps[appName] = (apps[appName][0],treeish)
        appsToUpdate[i] = appName


if not updateAll:
    for appName in appsToUpdate:
        if not appName in apps:
            logging.error(f"ERROR: You specified app name '{appName}' to update, but there is no configuration data in this program for an app of that name. Skipping")


for appName,v in apps.items():
    gitRepo            = v[0]
    gitRepoVersion     = v[1]
    postPipInstallWork = v[3]

    if not updateAll:
        if appName not in appsToUpdate:
            continue

    logging.info(f"Updating app: {appName}")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return os.path.join(appsFullPathDir,appName)
    myAppFullPathDir = run()
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.pwd()
    r = run()
    origDir = r.stdout.decode().strip()


    # TBD push out a notification to the app to tell any users that app
    # is stopping and will be updated


    # Stop service before doing update
    logging.info(f"Stopping service for {appName}")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.sudo(["systemctl","stop",appName])
    r = run()

    # Create backup dir
    logging.info("Creating backup dir ArchivedApps")
    archiveFullPathDir = os.path.join(appsFullPathDir, "ArchivedApps")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.mkdir("-p", archiveFullPathDir)
    r = run()

    logging.info(f"Creating backup dir ArchivedApps/{appName}")
    appArchiveFullPathDir = os.path.join(archiveFullPathDir, appName)
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.mkdir("-p", appArchiveFullPathDir)
    r = run()


    # Archive original app
    if os.path.exists(myAppFullPathDir):
        timeStamp = datetime.datetime.now().strftime("%m.%d.%y-%H.%M.%S.%f").strip()
        destPath = os.path.join(appArchiveFullPathDir, appName + "-" + timeStamp)
        logging.info(f"Archiving current app at {myAppFullPathDir} to {destPath}")
        @DeepRepipeStdErrAndStdOutToLogger
        def run(stdOut,stdErr):
            return sh.mv(myAppFullPathDir,destPath)
        r = run()

        # Delete archives older than delArchivesOlderThanDays
        @DeepRepipeStdErrAndStdOutToLogger
        def run(stdOut,stdErr):
            return sh.find(appArchiveFullPathDir, "-daystart", "-mindepth", 1, "-maxdepth", 1, "-iname", f"{appName}*", "-mtime", f"+{delArchivesOlderThanDays}", "-print")
        r = run()
        dirsToDelete = r.stdout.decode().strip().split("\n")

        # Filter out the empty string, which we get from prev find operation if there
        # were no matching files
        dirsToDelete = [d for d in dirsToDelete if len(d) > 0]

        if len(dirsToDelete) > 0:
            for d in dirsToDelete:
                logging.info(f"    Old archive file will be deleted: {d}")
                # TBD add the delete here. Holding of for now because rm is a bit dangerous.
                # Need to really test this first
        else:
            logging.info(f"There were no archived apps older than {delArchivesOlderThanDays} days old to delete")
    else:
        logging.info(f"App dir ({myAppFullPathDir}) doesn't exist, so skipped archiving it")


    # Clone repo
    logging.info(f"Cloning git repo {gitRepo} to {myAppFullPathDir}")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.git.clone(gitRepo,myAppFullPathDir)
    r = run()

    # Checkout specific version of code
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.cd(myAppFullPathDir)
    r = run()
    logging.info(f"Running git checkout for treeish {gitRepoVersion}")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.git.checkout(gitRepoVersion)
    r = run()


    # Recursive remove any of these specified files
    for fileName in filesToDelete:
        logging.info(f"Removing {fileName} files from {myAppFullPathDir}")
        # for some reason "rm -r" wasnt doing recursion
        @DeepRepipeStdErrAndStdOutToLogger
        def run(stdOut,stdErr):
            return sh.find(".","-name",fileName,"-delete")
        r = run()


    # Create venv
    logging.info(f"Creating a venv in {myAppFullPathDir}")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.python3("-m","venv","venv")
    r = run()


    # Upgrade pip
    logging.info("Upgrading the venv pip to latest...")
    pathToAppsPython = os.path.join(myAppFullPathDir,"venv/bin/python")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return os.system(f"{pathToAppsPython} -m pip install --upgrade pip")
    r = run()

    # Activate venv and then pip install required packages
    logging.info("Pip installing into venv the required packages...")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return os.system(f"cd {myAppFullPathDir}; . venv/bin/activate; pip install -r requirements.txt;")
    r = run()

    # If there is work to do after pip install, do that
    if postPipInstallWork:
        postPipInstallWork(myAppFullPathDir)

    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.cd(origDir)
    r = run()


    # Copy in the appropriate env file and minimized its access due to secrets in file
    if isDevServer:
        logging.info(f"Copying over the DEVELOPMENT env config file to {myAppFullPathDir}")
        sourceFile = "env.dev"
        destFile = ".env"
    elif isProdServer:
        logging.info(f"Copying over the PRODUCTION env config file to {myAppFullPathDir}")
        sourceFile = "env.prod"
        destFile = ".env"
    else:
        logging.error("ERROR, must be either DEV or PROD")
        sys.exit(-1)
    dst = os.path.join(myAppFullPathDir,destFile)
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.cp(sourceFile,dst)
    r = run()
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.chmod("go-rwx",dst)
    r = run()


    # Now start/enable/status for web app service
    logging.info(f"Start service for {appName}")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.sudo(["systemctl","start",appName])
    r = run()

    logging.info(f"Enable service for {appName}")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.sudo(["systemctl","enable",appName])
    r = run()

    logging.info(f"Check service status for {appName}")
    @DeepRepipeStdErrAndStdOutToLogger
    def run(stdOut,stdErr):
        return sh.sudo(["systemctl","status","-l","--no-pager",appName])
    r = run()


# TBD test web access
# TBD run app provided regression test on the web interface
