#!/usr/bin/python3
# -*- coding: utf-8 -*-
# fetch_data.py

"""
Query the Celestrak and space-track websites for up-to-date orbital elements for spacecraft.
"""

import calendar
import json
import logging
import os
import sys
import time

import satcat_fetch
from connect_db import connect_db


def read_tle_file(path, c, sat_mags, group, source):
    """
    Parse a two-line element (TLE) file and extract the list of orbital elements from it.

    :param path:
        The path of the TLE file we should parse
    :param c:
        A MySQLdb database connection handle
    :param sat_mags:
        A dictionary of the absolute magnitudes of spacecraft, indexed by their NORAD ID
    :param group:
        The name of the (sub)group of satellites contained within this TLE file
    :param source:
        The source ID number for these orbital elements
    :return:
        A list of lists containing the orbital elements we extracted from the file
    """

    items = []
    lines = open(path).readlines()
    line_count = 0

    while line_count < len(lines):
        # First line of a set of TLEs must start with "1 ". Celestrak intersperse TLEs with names
        if not lines[line_count].startswith("1 "):
            line_count += 1
            continue

        i = line_count - 1
        norad_id = int(lines[i + 1][2: 7])
        incl = float(lines[i + 2][8:16])
        ecc = float("0." + lines[i + 2][26:33])
        ra_asc = float(lines[i + 2][17:25])
        arg_peri = float(lines[i + 2][34:42])
        mean_anom = float(lines[i + 2][43:51])
        mean_motion = float(lines[i + 2][52:63])
        year = int("20" + lines[i + 1][18:20])
        day = float(lines[i + 1][20:32])

        mean_motion_dot = ((-1 if lines[i + 1][33] == "-" else 1) *
                           float(lines[i + 1][34:43]) * 2)

        mean_motion_dot_dot = ((-1 if lines[i + 1][44] == "-" else 1) *
                               float("0." + lines[i + 1][45:50] + "E" + lines[i + 1][50:52]) * 6)

        b_star = ((-1 if lines[i + 1][53] == "-" else 1) *
                  float("0." + lines[i + 1][54:59] + "E" + lines[i + 1][59:61]))

        rev_count = float(lines[i + 2][63:68])

        epoch = calendar.timegm((year, 1, 1, 0, 0, 0, 0, 0, 0))
        epoch += (day - 1) * 3600 * 24  # January 1st is day 1
        if norad_id in sat_mags:
            mag = sat_mags[norad_id]
        else:
            if group and group['subgroupname'] == 'Starlink':
                # Hard code a standard magnitude for all Starlink satellites!
                mag = 5.5
            else:
                mag = None

        items.append([
            group,
            norad_id,
            (norad_id, epoch, incl, ecc, ra_asc, arg_peri, mean_anom, mean_motion, mag,
             mean_motion_dot, mean_motion_dot_dot, b_star, source, rev_count),
        ])

        line_count += 2

    return items


def main_spacecraft(logger):
    """
    Main entry point to query the Celestrak and space-track websites for up-to-date orbital elements for spacecraft.

    :param logger:
        A logging object
    :return:
        None
    """

    # Read SATCAT from the Celestrak website. Build catalogue of all spacecraft
    logger.info("Fetching SATCAT")
    satcat_fetch.satcat_fetch()

    # Connect to database
    [db, c] = connect_db()
    c.execute("BEGIN;")

    # Make a persistent working directory
    tmpdir = "../auto/tmp/spacecraft"
    os.system("mkdir -p {}".format(tmpdir))

    # Fetch spacecraft magnitude data from Mike McCants's website
    sat_mags = {}
    utc_now = time.time()

    # First, mcnames file which has pessimistic magnitude estimates
    logger.info("Fetching mcnames")
    last_downloaded = 0
    try:
        last_downloaded = float(open("../auto/tmp/spacecraft/last_download_mcnames").read())
    except (ValueError, IOError):
        pass

    # Fetch new copy of mcnames if we've not downloaded it for 60 days
    if (utc_now > last_downloaded + 60 * 86400) or not os.path.exists("../auto/tmp/spacecraft/mcnames.zip"):
        # Download and unzip mcnames
        logger.info("Downloading new copy of mcnames")
        os.system("cd ../auto/tmp/spacecraft ; "
                  "rm -f mcnames.zip ; "
                  "wget -q http://www.prismnet.com/~mmccants/tles/mcnames.zip ; "
                  "unzip -o mcnames.zip")

        # Check that download went OK
        if not (os.path.exists("../auto/tmp/spacecraft/mcnames.zip") and
                os.path.exists("../auto/tmp/spacecraft/mcnames")):
            logger.info("!!! Problem downloading <mcnames> file. Reverting to old copy.")

            # If not, revert to backup copy
            if not os.path.exists("../auto/tmp/spacecraft/mcnames"):
                os.system("cd ../auto/tmp/spacecraft ; "
                          "cp ../../../data/spacecraft/mcnames.zip . ; "
                          "unzip -o mcnames.zip")
        else:
            open("../auto/tmp/spacecraft/last_download_mcnames", "w").write(str(utc_now))

    # Extract magnitudes of spacecraft from the mcnames file
    logger.info("Extracting magnitudes from mcnames")
    for line in open("../auto/tmp/spacecraft/mcnames"):
        try:
            sat_mags[int(line[0:5])] = float(line[37:42])
        except ValueError:
            pass

    # Continue fetching spacecraft magnitude data from Mike McCants's website
    # Secondly, download quicksat file which is more widely used and about 1.4 mag brighter
    # Use values in this file in preference to <mcnames>.
    logger.info("Fetching qs.mag")
    last_downloaded = 0
    try:
        last_downloaded = float(open("../auto/tmp/spacecraft/last_download_quicksat").read())
    except (ValueError, IOError):
        pass

    # Fetch new copy of quicksat if we've not downloaded it for 60 days
    if (utc_now > last_downloaded + 60 * 86400) or not os.path.exists("../auto/tmp/spacecraft/qsmag.zip"):
        # Download and unzip mcnames
        logger.info("Downloading new copy of qs.mag")
        os.system("cd ../auto/tmp/spacecraft ; "
                  "rm -f qsmag.zip ; "
                  "wget -q https://www.prismnet.com/~mmccants/programs/qsmag.zip ; "
                  "unzip -o qsmag.zip")

        # Check that download went OK
        if not (os.path.exists("../auto/tmp/spacecraft/qsmag.zip") and
                os.path.exists("../auto/tmp/spacecraft/qs.mag")):
            logger.info("!!! Problem downloading <qs.mag> file. Reverting to old copy.")

            # If not, revert to backup copy
            if not os.path.exists("../auto/tmp/spacecraft/qs.mag"):
                os.system("cd ../auto/tmp/spacecraft ; "
                          "cp ../../../data/spacecraft/qsmag.zip . ; "
                          "unzip -o qsmag.zip")
        else:
            open("../auto/tmp/spacecraft/last_download_quicksat", "w").write(str(utc_now))

    # Extract magnitudes of spacecraft from the qs.mag file
    logger.info("Extracting magnitudes from qs.mag")
    for line in open("../auto/tmp/spacecraft/qs.mag"):
        try:
            # Quicksat figures for full phase; formula in satcalc.js assumes reference mag at 90 deg phase
            sat_mags[int(line[0:5])] = float(line[33:37]) + 1.2428746817353344
        except ValueError:
            pass

    # Register epoch at which we fetched data
    epoch = time.time()
    c.execute("INSERT INTO spacecraft_epochs (epoch) VALUES (%s);", [epoch])
    epoch_id = db.insert_id()
    logger.info("Created epoch ID {:d}".format(epoch_id))

    # Recreate many-to-many table of membership of spacecraft groups
    c.execute("DELETE FROM spacecraft_leo_groupmembers;")

    # Fetch a list of all (sub)groups of LEOs, as listed in <satcat_abbrevs.xml> and copied to SQL above
    c.execute("SELECT g.name AS groupname, s.name AS subgroupname, s.url AS url "
              "FROM spacecraft_leo_subgroups s "
              "INNER JOIN spacecraft_leo_groups g ON s.parent=g.uid;")
    groups = c.fetchall()

    # Download TLEs for all spacecraft (sub)groups from the Celestrak website
    items = []
    for group in groups:

        # If URL takes the form of a lump of JSON, it is a list of the NORAD IDs of the spacecraft in this group
        if group["url"][0] == '[':
            for norad_id in json.loads(group["url"]):
                items.append([group, norad_id, False])

        # Otherwise it's the name of a text file that we need to download from the Celestrak website
        else:
            filename = group["url"]
            path = "{}/{}".format(tmpdir, filename)

            # See if we already have a copy of this file
            got_old = os.path.exists("{}/{}".format(tmpdir, filename))

            # If so, make a backup with a _old suffix
            if got_old:
                os.system("cd {} ; mv {} {}_old".format(tmpdir, filename, filename))

            # Fetch TLE file from Celestrak
            logger.info("Downloading Celestrak file <{}>".format(filename))
            os.system("cd {} ; wget -q https://www.celestrak.com/NORAD/elements/{}".format(tmpdir, filename))

            # If something went wrong, then restore backup file
            if (not os.path.exists(path)) or (len(open(path).readlines()) < 3):
                logger.info("!!! Download failed. Reverting to backup.")
                os.system("cd {} ; mv {}_old {}".format(tmpdir, filename, filename))

            # Read TLE file
            new_items = read_tle_file(path, c, sat_mags, group, 0)
            items.extend(new_items)

    # Download TLEs for all spacecraft from the space-track website
    last_downloaded = 0
    try:
        last_downloaded = float(open("../auto/tmp/spacecraft/last_download_spacetrack").read())
    except (ValueError, IOError):
        pass

    # Fetch new copy of quicksat if we've not downloaded it for 5 days
    if (utc_now > last_downloaded + 5 * 86400) or not os.path.exists("../auto/tmp/spacecraft/spacetrack.tle"):
        # Download space track TLE file
        logger.info("Downloading space track TLE file")
        os.system("cd ../auto/tmp/spacecraft ; "
                  "rm -f spacetrack.tle ; "
                  "wget -q "
                  "--post-data='identity=INSERT_USERNAME_HERE&password=INSERT_PASSWORD_HERE&"
                  "query=https://www.space-track.org/basicspacedata/query/class/tle_latest/ORDINAL/1/EPOCH/%3Enow-30/orderby/NORAD_CAT_ID/format/tle' "
                  "--cookies=on --keep-session-cookies --save-cookies=/tmp/st-cookies.txt 'https://www.space-track.org/ajaxauth/login' "
                  "-O spacetrack.tle"
                  )

        # Check that download went OK
        if not os.path.exists("../auto/tmp/spacecraft/spacetrack.tle"):
            logger.info("!!! Problem downloading space-track TLE file.")
        else:
            open("../auto/tmp/spacecraft/last_download_spacetrack", "w").write(str(utc_now))

            # Read TLE file
            logger.info("Adding TLEs from spacetrack")
            new_items = read_tle_file("../auto/tmp/spacecraft/spacetrack.tle", c, sat_mags, None, 1)
            items.extend(new_items)

    # Now add each set of TLEs to the database
    logger.info("Importing TLEs into database")
    downloaded_elements = 0
    inserted_elements = 0
    unchanged_elements = 0
    for (group, norad_id, elements) in items:
        # Check that spacecraft is in table
        c.execute("SELECT 1 FROM spacecraft WHERE noradId=%s;", (norad_id,))
        result = c.fetchall()
        if len(result) < 1:
            continue

        # Add orbital data for this epoch
        if elements:
            downloaded_elements += 1
            # If we already have an orbit for this spacecraft at this epoch, we don't need another
            c.execute("SELECT orbitId FROM spacecraft_orbit_epochs WHERE noradId=%s AND epochId=%s;",
                      (norad_id, epoch_id))
            result = c.fetchall()
            if len(result) < 1:
                # If we already have a copy of this spacecraft orbit, count it as a duplicate
                c.execute("""
SELECT uid FROM spacecraft_orbits WHERE noradId=%s AND epoch BETWEEN (%s-1) AND (%s+1);
""", (norad_id, elements[1], elements[1]))
                result = c.fetchall()
                if len(result) < 1:
                    # New orbit, so create new record for it
                    c.execute("""
INSERT INTO spacecraft_orbits (noradId,epoch,incl,ecc,RAasc,argPeri,meanAnom,meanMotion,mag,
                                        meanMotionDot,meanMotionDotDot,bStar,source,revCount)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
""", elements)
                    orbit_id = db.insert_id()
                    is_duplicate = False
                    inserted_elements += 1
                else:
                    # Old orbit, so copy it as a duplicate
                    orbit_id = result[0]['uid']
                    is_duplicate = True
                    unchanged_elements += 1

                # Register orbit for this spacecraft, epoch combination
                c.execute("INSERT INTO spacecraft_orbit_epochs (noradId, epochId, orbitId, duplicate)"
                          "VALUES (%s,%s,%s,%s);",
                          (norad_id, epoch_id, orbit_id, is_duplicate))

        # Populate one-to-many table with group that this spacecraft is in
        if group:
            c.execute("INSERT INTO spacecraft_leo_groupmembers (noradId, groupId) "
                      "VALUES (%s,(SELECT uid FROM spacecraft_leo_subgroups WHERE name=%s));",
                      (norad_id, group["subgroupname"]))

    # Check for spacecraft which had orbits in previous epochId, but not this one
    duplicated_elements = satcat_fetch.duplicate_elements(logger=logger, c=c,
                                                          epoch=epoch, epoch_id=epoch_id)

    # Display a report of how many spacecraft we fetched in each group
    logger.info("Downloaded elements: {:d}".format(downloaded_elements))
    logger.info("Unchanged elements: {:d}".format(unchanged_elements))
    logger.info("Inserted elements: {:d}".format(inserted_elements))
    logger.info("Duplicate elements: {:d}".format(duplicated_elements))
    for group in groups:
        c.execute("SELECT COUNT(*) FROM spacecraft_leo_groupmembers "
                  "WHERE groupId=(SELECT uid FROM spacecraft_leo_subgroups WHERE name=%s);",
                  (group["subgroupname"],))
        logger.info(" {:24s} {:58s} -- {:6d} spacecraft".
                    format(group["groupname"], group["subgroupname"], c.fetchone()["COUNT(*)"]))

    # Commit databases
    logger.info("Cleaning up")
    c.execute("COMMIT;")
    db.commit()
    db.close()


# Do it right away if we're run as a script
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        stream=sys.stdout,
                        format='[%(asctime)s] %(levelname)s:%(filename)s:%(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S')
    logger = logging.getLogger(__name__)
    logger.info(__doc__.strip())

    main_spacecraft(logger=logger)
