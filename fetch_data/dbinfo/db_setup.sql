DROP USER IF EXISTS 'satcat'@'localhost';
CREATE USER 'satcat'@'localhost' IDENTIFIED BY 'ajohB2ei';
DROP DATABASE IF EXISTS satcat;
CREATE DATABASE satcat;
GRANT ALL ON satcat.* TO 'satcat'@'localhost';

DROP USER IF EXISTS 'satcat_read'@'localhost';
CREATE USER 'satcat_read'@'localhost' IDENTIFIED BY 'iul7Rai7';
GRANT SELECT ON satcat.* TO 'satcat_read'@'localhost';

