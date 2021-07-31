/* schema.sql */

BEGIN;

/* Create table of spacecraft */
CREATE TABLE spacecraft_owners
(
    uid    SMALLINT PRIMARY KEY AUTO_INCREMENT,
    abbrev TEXT(10),
    name   TEXT(100)
);

CREATE TABLE spacecraft_launchsites
(
    uid    SMALLINT PRIMARY KEY AUTO_INCREMENT,
    abbrev TEXT(10),
    name   TEXT(100)
);

CREATE TABLE spacecraft_statuses
(
    uid    TINYINT PRIMARY KEY AUTO_INCREMENT,
    abbrev TEXT(10),
    name   TEXT(30)
);

CREATE TABLE spacecraft_orbital_parent
(
    uid       SMALLINT PRIMARY KEY AUTO_INCREMENT,
    abbrev    TEXT(10),
    name      TEXT(30),
    adjective TEXT(30)
);

CREATE TABLE spacecraft_orbital_fate
(
    uid    TINYINT PRIMARY KEY AUTO_INCREMENT,
    abbrev TEXT(10),
    name   TEXT(30)
);

CREATE TABLE spacecraft
(
    noradId           INTEGER PRIMARY KEY AUTO_INCREMENT,
    cosparId          VARCHAR(15) UNIQUE,
    launchDate        REAL,
    decayDate         REAL,
    owner             SMALLINT,
    launchSite        SMALLINT,
    operationalStatus TINYINT,
    orbitalParent     SMALLINT,
    orbitalFate       TINYINT,
    orbitalPeriod     REAL,
    isDebris          BOOLEAN,
    INDEX (cosparId),
    FULLTEXT INDEX (cosparId),
    INDEX (decayDate),
    FOREIGN KEY (owner) REFERENCES spacecraft_owners (uid),
    FOREIGN KEY (launchSite) REFERENCES spacecraft_launchsites (uid),
    FOREIGN KEY (operationalStatus) REFERENCES spacecraft_statuses (uid),
    FOREIGN KEY (orbitalParent) REFERENCES spacecraft_orbital_parent (uid),
    FOREIGN KEY (orbitalFate) REFERENCES spacecraft_orbital_fate (uid)
);

CREATE TABLE spacecraft_epochs
(
    uid   INTEGER PRIMARY KEY AUTO_INCREMENT,
    epoch REAL NOT NULL,
    INDEX (epoch)
);

CREATE TABLE spacecraft_orbits
(
    uid              INTEGER PRIMARY KEY AUTO_INCREMENT,
    noradId          INTEGER NOT NULL,
    epoch            REAL    NOT NULL,
    incl             REAL,
    ecc              REAL,
    RAasc            REAL,
    argPeri          REAL,
    meanAnom         REAL,
    meanMotion       REAL,
    meanMotionDot    REAL,
    meanMotionDotDot REAL,
    bStar            REAL,
    mag              REAL,
    revCount         INTEGER,
    source           TINYINT,
    INDEX (noradId, epoch),
    FOREIGN KEY (noradId) REFERENCES spacecraft (noradId) ON DELETE CASCADE
);

CREATE TABLE spacecraft_orbit_epochs
(
    orbitId   INTEGER NOT NULL,
    epochId   INTEGER NOT NULL,
    noradId   INTEGER NOT NULL,
    duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (orbitId) REFERENCES spacecraft_orbits (uid) ON DELETE CASCADE,
    FOREIGN KEY (epochId) REFERENCES spacecraft_epochs (uid) ON DELETE CASCADE,
    PRIMARY KEY (noradId, epochId),
    FOREIGN KEY (noradId) REFERENCES spacecraft (noradId) ON DELETE CASCADE
);

CREATE TABLE spacecraft_leo_groups
(
    uid  INTEGER PRIMARY KEY AUTO_INCREMENT,
    name TEXT(60) NOT NULL
);

CREATE TABLE spacecraft_leo_subgroups
(
    uid    INTEGER PRIMARY KEY AUTO_INCREMENT,
    name   TEXT(60) NOT NULL,
    parent INTEGER  NOT NULL,
    url    TEXT(100),
    FOREIGN KEY (parent) REFERENCES spacecraft_leo_groups (uid) ON DELETE CASCADE
);

CREATE TABLE spacecraft_leo_groupmembers
(
    uid     INTEGER PRIMARY KEY AUTO_INCREMENT,
    noradId INTEGER NOT NULL,
    groupId INTEGER NOT NULL,
    UNIQUE (noradId, groupId),
    FOREIGN KEY (noradId) REFERENCES spacecraft (noradId) ON DELETE CASCADE,
    FOREIGN KEY (groupId) REFERENCES spacecraft_leo_subgroups (uid) ON DELETE CASCADE
);

CREATE TABLE spacecraft_names
(
    uid         INTEGER PRIMARY KEY AUTO_INCREMENT,
    noradId     INTEGER,
    name        VARCHAR(256),
    primaryName TINYINT,
    source      TINYINT,
    FULLTEXT INDEX (name),
    INDEX (name),
    FOREIGN KEY (noradId) REFERENCES spacecraft (noradId) ON DELETE CASCADE
);

COMMIT;
