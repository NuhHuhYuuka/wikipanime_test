#!/bin/sh
set -e

echo "Starting MySQL server..."
service mariadb start

echo "Waiting for MySQL to be ready..."
until mysql -u root -e "SELECT 1" >/dev/null 2>&1; do
    sleep 1
done

echo "Setting up database..."
mysql -u root -e "CREATE DATABASE IF NOT EXISTS wikipanime;"
mysql -u root -e "CREATE USER IF NOT EXISTS 'yuwkaa'@'localhost' IDENTIFIED BY 'fake_db_password';"
mysql -u root -e "GRANT ALL PRIVILEGES ON wikipanime.* TO 'yuwkaa'@'localhost';"

# Kiem tra xem file init.sql co ton tai khong truoc khi nap
if [ -f "/tmp/init.sql" ]; then
    echo "Loading data from init.sql..."
    mysql -u root wikipanime < /tmp/init.sql
    
    echo "Removing init.sql..."
    rm -f /tmp/init.sql
else
    echo "init.sql not found. Database is already initialized, skipping..."
fi

echo "Starting Flask as user gugugaga2452..."
su gugugaga2452 -c "python3 app.py"