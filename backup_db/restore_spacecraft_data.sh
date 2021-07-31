#!/bin/bash

# Restore orbital elements from a JSON archive generated with
# <saveSpacecraftData_v5.py> into the current database.

zcat satellite_data.sql.gz | mysql --defaults-extra-file=../auto/mysql_login.cfg satcat

