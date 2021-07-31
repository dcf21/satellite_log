# -*- coding: utf-8 -*-
# satcat_fetch.py

"""
Functions to download SATCAT -- i.e. a listing of all spacecraft with NORAD ID numbers -- from the Celestrak website,
and insert them all into the spacecraft table in the database.
"""

import datetime
import os
import re
import time

from connect_db import connect_db
from vendor import xmltodict


# For more information, see:

# http://www.celestrak.com/satcat/sources.asp
# http://www.celestrak.com/satcat/launchsites.asp
# http://www.celestrak.com/satcat/status.asp

def insert_name(c, norad_id, name, source, primary):
    """
    Insert into the database a new name for a spacecraft. If the name is of the form foo(bar), we automatically import
    foo and bar into the table of names as two separate entries.

    :param c:
        A MySQLdb database connection handle
    :param norad_id:
        The NORAD ID of the spacecraft we are to add a new name for
    :param name:
        The name we are to add for this spacecraft
    :param source:
        The numerical source ID for this name
    :param primary:
        Boolean flag indicating whether this is the primary name by which we should refer to this spacecraft
    :return:
        None
    """
    # If name has string in ()-brackets following it, treat that as an alternative name
    test = re.match(r"(.*)\((...*)\)", name)
    if test:
        insert_name(c=c, norad_id=norad_id, name=test.group(2), source=source, primary=0)
        name = test.group(1)

    # If name has string in []-brackets following it, treat that as an alternative name
    test = re.match(r"(.*)\[(...*)\]", name)
    if test:
        insert_name(c=c, norad_id=norad_id, name=test.group(2), source=source, primary=0)
        name = test.group(1)

    # If this is a primary name, remove any other primary names
    if primary:
        c.execute("UPDATE spacecraft_names SET primaryName=0 WHERE noradId=%s;", (norad_id,))

    # Insert this name
    c.execute("INSERT INTO spacecraft_names (noradId,name,source,primaryName) VALUES (%s,%s,%s,%s);",
              (norad_id, name.strip(), source, primary))

    # If this name contains the string "DEB", we mark this spacecraft is being debris
    if " DEB" in name:
        c.execute("UPDATE spacecraft SET isDebris=1 WHERE noradId=%s;", (norad_id,))


def satcat_fetch():
    """
    Main entry point for downloading SATCAT and importing its contents into the database.

    :return:
        None
    """

    # Make working directory
    tmpdir = "../auto/tmp/satellites"
    os.system("mkdir -p {}".format(tmpdir))

    # Open database
    [db, c] = connect_db()
    c.execute("BEGIN;")

    # Ensure all data is transferred from XML to database
    # Read source XML data
    pwd = os.getcwd()
    xml_file = open(os.path.join(pwd, "../satellite_data/satcat_abbrevs.xml"), "rb")
    xml = xmltodict.parse(xml_file)

    # Loop over tags in XML file feeding names of items into SQL
    for [table_name, xml_name] in [["spacecraft_statuses", "satelliteStatus"],
                                   ["spacecraft_owners", "satelliteOwners"],
                                   ["spacecraft_launchsites", "launchSites"],
                                   ["spacecraft_orbital_fate", "orbitalFates"],
                                   ["spacecraft_orbital_parent", "orbitalParents"]]:
        for item in xml['satcat'][xml_name]['item']:
            # Check whether this item already exists in the database
            c.execute("SELECT 1 FROM " + table_name + " WHERE abbrev=%s", (item['abbrev'],))
            # Update or add name for this item
            if len(c.fetchall()) > 0:
                c.execute("UPDATE " + table_name + " SET name=%s WHERE abbrev=%s;",
                          (item['name'], item['abbrev']))
            else:
                c.execute("INSERT INTO " + table_name + " (abbrev,name) VALUES (%s, %s);",
                          (item['abbrev'], item['name']))
            # Orbital destinations also have adjectival forms, e.g. "Jovian" for Jupiter
            if 'adjective' in item:
                c.execute("UPDATE " + table_name + " SET adjective=%s WHERE abbrev=%s;",
                          (item['adjective'], item['abbrev']))

    # Celestrak divides satellites into (sub)groups, which are listed here: https://www.celestrak.com/NORAD/elements/
    # The XML file lists all of these (sub)groups which we use to populate the leo_groups table
    # Loop over these groups one by one
    for item in xml['satcat']['leoGroups']['item']:
        # Make sure that a group of this name exists in the leo_groups table
        while True:
            c.execute("SELECT uid FROM spacecraft_leo_groups WHERE name=%s;", (item['group'],))
            result = c.fetchall()
            if len(result) > 0:
                group_id = result[0]["uid"]
                break
            c.execute("INSERT INTO spacecraft_leo_groups VALUES (DEFAULT, %s);", (item['group'],))

        # Make sure that a subgroup of this name exists in the leo_groups table
        c.execute("SELECT uid FROM spacecraft_leo_subgroups WHERE parent=%s AND name=%s;",
                  (group_id, item['subgroup']))
        result = c.fetchall()
        if len(result) == 0:
            c.execute("INSERT INTO spacecraft_leo_subgroups VALUES (DEFAULT, %s, %s, %s);",
                      (item['subgroup'], group_id, item['url']))
        else:
            subgroup_id = result[0]["uid"]
            c.execute("UPDATE spacecraft_leo_subgroups SET url=%s WHERE uid=%s;", (item['url'], subgroup_id,))

    # Fetch list of satellites from SATCAT, as hosted on the Celestrak website
    os.system("rm -f ../auto/tmp/satellites/satcat.txt")
    os.system("cd ../auto/tmp/satellites ; wget -q http://www.celestrak.com/pub/satcat.txt")

    # Loop over the lines in SATCAT file we've just downloaded
    if os.path.exists("../auto/tmp/satellites/satcat.txt"):
        for line in open("../auto/tmp/satellites/satcat.txt"):
            cospar_id = line[0:11].strip()
            norad_id = int(line[13:18])
            status = line[21:22].strip()
            name = line[23:47].strip()
            owner = line[49:54].strip()
            lsite = line[68:73].strip()

            # Convert launch date into a unix time
            launch_year = line[56:60].strip()
            launch_month = line[61:63]
            launch_day = line[64:66]
            if launch_year:
                launch = time.mktime(datetime.datetime(year=int(launch_year), month=int(launch_month),
                                                       day=int(launch_day)).timetuple())
            else:
                launch = None

            # Convert decay date into a unix time
            decay_year = line[75:79].strip()
            decay_month = line[80:82]
            decay_day = line[83:85]
            if decay_year:
                decay = time.mktime(datetime.datetime(year=int(decay_year), month=int(decay_month),
                                                      day=int(decay_day)).timetuple())
            else:
                decay = None

            # Basic orbit details are held in SATCAT
            orbit = line[129:].strip()
            orbit_parent = orbit_fate = orbit_period = None
            if (len(orbit) == 3) and (orbit != "NEA"):
                orbit_parent = orbit[0:2]
                orbit_fate = orbit[2]
            orbit_period_str = line[87:94]
            try:
                orbit_period = float(orbit_period_str)
            except ValueError:
                pass

            # See whether this satellite is already in the spacecraft table. If no, create a stub entry for it
            c.execute("SELECT noradId FROM spacecraft WHERE noradId=%s;", (norad_id,))
            result = c.fetchall()
            if len(result) < 1:
                c.execute("INSERT INTO spacecraft (noradId) VALUES (%s);", (norad_id,))

            # If there is already another spacecraft with the same cospar Id, delete it...
            c.execute("SELECT noradId FROM spacecraft WHERE cosparId=%s AND NOT noradId=%s;",
                      (cospar_id, norad_id))
            for item in c.fetchall():
                print("!!! Deleting noradId {:d} because it shares cosparId {:s} with {:d}.".format(item['noradId'],
                                                                                                    cospar_id,
                                                                                                    norad_id))
                c.execute("DELETE FROM spacecraft WHERE noradId=%s;", (item['noradId'],))

            # Insert new data for this spacecraft into the table
            c.execute("""
UPDATE spacecraft SET cosparId=%s, launchDate=%s, decayDate=%s,
   OWNER=(SELECT uid FROM spacecraft_owners WHERE abbrev=%s),
   launchSite=(SELECT uid FROM spacecraft_launchsites WHERE abbrev=%s),
   operationalStatus=(SELECT uid FROM spacecraft_statuses WHERE abbrev=%s),
   orbitalParent=(SELECT uid FROM spacecraft_orbital_parent WHERE abbrev=%s),
   orbitalFate=(SELECT uid FROM spacecraft_orbital_fate WHERE abbrev=%s),
   orbitalPeriod=%s, isDebris=0
WHERE noradId=%s;
    """, (cospar_id, launch, decay, owner, lsite, status, orbit_parent, orbit_fate, orbit_period, norad_id))

            # Remove all names we previously held for this spacecraft
            c.execute("""
DELETE FROM spacecraft_names WHERE source=0 AND noradId=%s;
    """, (norad_id,))

            # Insert name of spacecraft as it appears in SATCAT
            insert_name(c=c, norad_id=norad_id, name=name, source=0, primary=1)

    # The Celestrak website hosts a "SATCAT Annex" which lists additional names of spacecraft
    # We fetch this catalogue, and add the additional names into the spacecraft_names table

    # Fetch catalogue
    os.system("rm -f ../auto/tmp/satellites/satcat-annex.txt")
    os.system("cd ../auto/tmp/satellites ; wget -q http://www.celestrak.com/pub/satcat-annex.txt")

    if os.path.exists("../auto/tmp/satellites/satcat-annex.txt"):

        # Delete all non-primary names for spacecraft
        c.execute("DELETE FROM spacecraft_names WHERE source=1;")

        # Loop over lines in SATCAT annex
        for annex in ["../satellite_data/spacecraft-extra-names.txt", "../auto/tmp/satellites/satcat-annex.txt"]:
            for line in open(annex):
                # Ignore blank lines or comment lines
                line = line.strip()
                if (len(line) == 0) or (line[0] == "#"):
                    continue
                bits = line.split("|")
                norad_id = int(bits[0])
                # Make sure that spacecraft actually exists in database
                c.execute("SELECT noradId FROM spacecraft WHERE noradId=%s;", (norad_id,))
                if c.rowcount > 0:
                    for alt_name in bits[1:]:
                        alt_name = alt_name.strip()
                        if alt_name.startswith("*"):
                            primary = 1
                            alt_name = alt_name[1:]
                        else:
                            primary = 0
                        if alt_name:
                            insert_name(c=c, norad_id=norad_id, name=alt_name, source=1, primary=primary)

    # Commit databases
    c.execute("COMMIT;")
    db.commit()
    db.close()


def duplicate_elements(logger, c, epoch, epoch_id, maximum_age_days=10):
    """
    Some spacecraft may not be queried at some epochs. Where this is the case, we duplicate the elements from the
    previous epoch.

    :param logger:
        A logging object
    :param c:
        A MySQLdb database connection handle
    :param epoch:
        The unix time of the epoch we are to insert newly duplicated elements into
    :param epoch_id:
        The database ID of this epoch
    :param maximum_age_days:
        The maximum allowed age of elements before we stop duplicating them and assume the spacecraft is dead
    :return:
        The number of elements which we duplicated
    """
    # Check for spacecraft which had orbits in previous epochId, but not this one
    logger.info("Checking for spacecraft for which we haven't downloaded elements at epoch {}".
                format(datetime.datetime.fromtimestamp(epoch).strftime("%d %b %Y %H:%M")))

    # Clear out any pre-existing duplicate elements from this epoch
    c.execute("DELETE FROM spacecraft_orbit_epochs WHERE duplicate AND epochId=%s;", (epoch_id,))

    # Find the epoch immediately preceding the present one, and copy spacecraft from there
    duplicated_elements = 0
    c.execute("SELECT uid FROM spacecraft_epochs WHERE epoch<%s ORDER BY epoch DESC LIMIT 1;", (epoch - 1,))
    previous_epoch_list = c.fetchall()
    if not previous_epoch_list:
        return 0

    previous_epoch = previous_epoch_list[0]['uid']

    # Search for spacecraft in preceding epoch, which are still missing from the present epoch
    c.execute("""
SELECT orbitId, noradId
FROM spacecraft_orbit_epochs
WHERE epochId=%s AND noradId NOT IN
(SELECT noradId
 FROM spacecraft_orbit_epochs
 WHERE epochId=%s);
""", (previous_epoch, epoch_id))

    for elements in c.fetchall():
        uid = elements['orbitId']
        norad_id = elements['noradId']

        # Check the first epoch where each set of orbital elements was first recorded
        c.execute("""
SELECT epoch
FROM spacecraft_orbit_epochs oe
INNER JOIN spacecraft_epochs e ON oe.epochId = e.uid
WHERE oe.orbitId=%s AND NOT oe.duplicate
        """, (uid,))

        # Ignore this spacecraft if we haven't seen new orbital elements for 10 days
        original_epoch = c.fetchall()
        if (not original_epoch) or (original_epoch[0]['epoch'] < epoch - maximum_age_days * 24 * 3600):
            continue

        # Copy this spacecraft's orbital elements into the new epoch
        duplicated_elements += 1
        c.execute("""
INSERT INTO spacecraft_orbit_epochs (noradId, epochId, orbitId, duplicate) VALUES (%s,%s,%s,1);
""", (norad_id, epoch_id, uid))
    logger.info("Duplicated {:d} elements".format(duplicated_elements))
    return duplicated_elements


# Do it right away if we're run as a script
if __name__ == "__main__":
    satcat_fetch()
