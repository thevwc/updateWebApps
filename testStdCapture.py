import sys
import os
import sh
from io import StringIO
from wurlitzer import pipes
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-7s %(message)s',
                    datefmt='%m-%d-%Y %I:%M:%S %p',
                    handlers=[logging.FileHandler("logging.log", mode='w'),logging.StreamHandler(sys.stdout)])

logging.debug  ('This message should go to the log file')
logging.info   ('So should this')
logging.warning('And this, too')
logging.error  ('And non-ASCII stuff, too, like Øresund and Malmö')


# Raise level to INFO because DEBUG level resulted in spew from sh
logging.getLogger().setLevel(logging.INFO)

pipesStdOut = StringIO()
pipesStdErr = StringIO()
with pipes(stdout=pipesStdOut, stderr=pipesStdErr):
   print("pipes print")
   os.system("echo hello world")
   sh.echo("echo hello",_out=pipesStdOut)

for v in pipesStdOut.getvalue().splitlines():
    logging.info(v)
for v in pipesStdErr.getvalue().splitlines():
    logging.error(v)

