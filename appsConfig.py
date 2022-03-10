"""
   Update this with your apps

   nameOfApp : (repo URL, default branch to checkout)
"""

import os

def EducationAppPostPipWork(installationDir):
    """
    This is a hack, but fixup sh to emit its output at debug and not info level so
    that we arn't spammed withi its debug logging.
    """
    print("Post pip install, patching sh package")
    filePath = os.path.join(installationDir, "venv/lib/python3.8/site-packages/sh.py")
    r = os.system(f"patch {filePath} <sh-1.14.2.patch")
    if r != 0:
        print("ERROR, patch of sh failed")

apps = {
    "Education" : ("https://github.com/thevwc/EducationWebApp.git", "main", EducationAppPostPipWork)
}
