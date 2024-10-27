# Overview

This tries to re-create a crontab content in case you "succesfully" but unintentionally deleted/reset your crontab, e.g. by using `crontab -r` instead of `crontab -e`.

Currently it works only on debian based systems.

This script is far from perfect. Feel free to improve :-)

# Execution 
`sudo python3 crontab-recreate.py`

`sudo` is necessary because logs are usually only readable for `root`.

This will result in crontab files for each user found in the logs.

Re-import using 
`crontab <filename>`
