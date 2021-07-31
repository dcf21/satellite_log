#!/usr/bin/python3
# -*- coding: utf-8 -*-
# initialize.py

import os

from connect_db import db_name, db_user, db_passwd, db_host


def make_mysql_login_config():
    """
    Create MySQL configuration file with username and password, which means we can log into database without
    supplying these on the command line.

    :return:
        None
    """

    pwd = os.getcwd()
    db_config = os.path.join(pwd, "../auto/mysql_login.cfg")

    config_text = """
[client]
user = {:s}
password = {:s}
host = {:s}
default-character-set = utf8mb4
""".format(db_user, db_passwd, db_host)
    open(db_config, "w").write(config_text)


def init_schema():
    """
    Create database tables, using schema defined in <schema.sql>.

    :return:
        None
    """

    pwd = os.getcwd()
    sql = os.path.join(pwd, "schema.sql")
    db_config = os.path.join(pwd, "../auto/mysql_login.cfg")

    # Create mysql login config file
    make_mysql_login_config()

    # Recreate database from scratch
    cmd = "echo 'DROP DATABASE IF EXISTS {:s};' | mysql --defaults-extra-file={:s}".format(db_name, db_config)
    os.system(cmd)
    cmd = ("echo 'CREATE DATABASE {:s} CHARACTER SET utf8mb4;' | mysql --defaults-extra-file={:s}".
           format(db_name, db_config))
    os.system(cmd)

    # Create basic database schema
    cmd = "cat {:s} | mysql --defaults-extra-file={:s} {:s}".format(sql, db_config, db_name)
    os.system(cmd)


# Do it right away if we're run as a script
if __name__ == "__main__":
    init_schema()
