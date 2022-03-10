#!/bin/sh

# Run this to do pip install because we have to patch one of the packages

pip install -r requirements.txt
patch venv/lib/python3.6/site-packages/sh.py <sh-1.14.2.patch
