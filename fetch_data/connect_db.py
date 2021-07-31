# -*- coding: utf-8 -*-
# connect_db.py

import os
import re
import sys
# Ignore SQL warnings
import warnings
from os import path as os_path

import MySQLdb

warnings.filterwarnings("ignore", ".*Unknown table .*")

# Fetch path to database profile
our_path = os_path.split(os_path.abspath(__file__))[0]
root_path = re.match(r"(.*satellite_log/)", our_path).group(1)
if not os.path.exists(os_path.join(root_path, "fetch_data/dbinfo/db_profile")):
    sys.stderr.write(
        "You must create a file <db_profile> in <fetch_data/dbinfo> to specify which database profile to use.\n")
    sys.exit(1)
db_profile = open(os_path.join(root_path, "fetch_data/dbinfo/db_profile")).read().strip()
if not os.path.exists(os_path.join(root_path, "fetch_data/dbinfo/db_profile_%s" % db_profile)):
    sys.stderr.write("File <db_profile> in <fetch_data/dbinfo> names an invalid profile.\n")
    sys.exit(1)

# Look up MySQL database log in details
db_login = open(os_path.join(root_path, "fetch_data/dbinfo/db_profile_%s" % db_profile)).read().split('\n')
db_host = "localhost"
db_user = db_login[0].strip()
db_passwd = db_login[1].strip()
db_name = db_login[2].strip()


# Open database
def connect_db():
    """
    Return a new MySQLdb connection to the database.

    :return:
        List of [database handle, connection handle]
    """

    global db_host, db_name, db_passwd, db_user
    db = MySQLdb.connect(host=db_host, user=db_user, passwd=db_passwd, db=db_name)
    c = db.cursor(cursorclass=MySQLdb.cursors.DictCursor)

    db.set_character_set('utf8mb4')
    c.execute('SET NAMES utf8mb4;')
    c.execute('SET CHARACTER SET utf8mb4;')
    c.execute('SET character_set_connection=utf8mb4;')

    return [db, c]


# Fetch the ID number associated with a particular data generator string ID
def fetch_generator_key(c, gen_key):
    """
    Return the ID number associated with a particular data generator string ID. Used to track which python scripts
    generate which entries in the database.

    :param c:
        MySQLdb database connection.
    :param gen_key:
        String data generator identifier.
    :return:
        Numeric data generator identifier.
    """

    c.execute("SELECT generatorId FROM inthesky_generators WHERE name=%s;", (gen_key,))
    tmp = c.fetchall()
    if len(tmp) == 0:
        c.execute("INSERT INTO inthesky_generators VALUES (NULL, %s);", (gen_key,))
        c.execute("SELECT generatorId FROM inthesky_generators WHERE name=%s;", (gen_key,))
        tmp = c.fetchall()
    gen_id = tmp[0]["generatorId"]
    return gen_id


# Fetch the ID number associated with a particular data source
def fetch_source_id(c, source_info):
    """
    Return the ID number associated with a particular data source string ID. Used to track which scientific sources
    generate which entries in the database.

    :param c:
        MySQLdb database connection.
    :param source_info:
        String data source identifier.
    :return:
        Numeric data source identifier.
    """

    [source_abbrev, source_name, source_url] = source_info

    if source_abbrev is None:
        return None

    c.execute("SELECT sourceId FROM inthesky_sources WHERE abbrev=%s;", (source_abbrev,))
    tmp = c.fetchall()
    if len(tmp) == 0:
        c.execute("INSERT INTO inthesky_sources VALUES (NULL, %s, %s, %s);",
                  (source_abbrev, source_name, source_url))
        c.execute("SELECT sourceId FROM inthesky_sources WHERE abbrev=%s;", (source_abbrev,))
        tmp = c.fetchall()
    source_id = tmp[0]["sourceId"]
    return source_id


# Fetch the ID number associated with a particular photometric band
def fetch_photometric_band_id(c, band_name):
    """
    Return the ID number associated with a particular photometric band.

    :param c:
        MySQLdb database connection.
    :param band_name:
        Name of photometric band (string).
    :return:
        Numeric photometric band identifier.
    """

    c.execute("SELECT uid FROM inthesky_photometric_bands WHERE name=%s;", (band_name,))
    tmp = c.fetchall()
    if len(tmp) == 0:
        c.execute("INSERT INTO inthesky_photometric_bands VALUES (NULL, %s);", (band_name,))
        c.execute("SELECT uid FROM inthesky_photometric_bands WHERE name=%s;", (band_name,))
        tmp = c.fetchall()
    band_id = tmp[0]["uid"]
    return band_id
