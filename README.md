# Satellite orbital elements archive

This is a quick-and-dirty SQL database I built for storing the historical
orbital elements of satellites, including a script for trawling data from
Celestrak and Space Track to populate the database. These scripts are used for
managing the archive of satellite data displayed on the website
[https://in-the-sky.org](https://in-the-sky.org).

## Setup

### 1. Database creation

```
# Create MySQL database and users we will use
cat fetch_data/dbinfo/db_setup.sql | sudo mysql -u root
```

### 2. Create database schema

```
cd fetch_data
./initialize.py
```

### 3. Supply credentials to use when fetching data from Space Track

The Space Track website requires all users to agree to their terms and
conditions, and individually obtain a username and password to access data. You
need to edit the file `fetch_data.py` (line 261) to insert these credentials
into the curl request.

Alternatively, if you only wish to fetch orbital elements from CelesTrak, you
can simply comment out the curl request to Space Track (lines 254-276 of
`fetch_data.py`).

### 4. Fetch orbital elements

```
cd fetch_data
./fetch_data.py
```

Now, simply run `fetch_data.py` as often as you want to fetch the latest
orbital elements into your data archive (perhaps daily).

### 5. Retrieving orbital elements

There's currently no API for this other than making direct SQL queries to the
database, but the schema of the data is pretty obvious!

