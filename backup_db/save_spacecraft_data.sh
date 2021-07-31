#!/bin/bash

# Export the spacecraft orbital elements we have in the database into a
# archive which we can subsequently reload.

mysqldump --defaults-extra-file=../auto/mysql_login.cfg satcat spacecraft spacecraft_epochs spacecraft_launchsites spacecraft_leo_groupmembers spacecraft_leo_groups spacecraft_leo_subgroups spacecraft_names spacecraft_orbit_epochs spacecraft_orbital_fate spacecraft_orbital_parent spacecraft_orbits spacecraft_owners spacecraft_statuses | gzip > satellite_data.sql.gz

