#!/bin/bash

# Start the first process
env > /etc/.cronenv
sed -i 's/\"/\\"/g' /etc/.cronenv
cat /dev/urandom | tr -dc 'a-f0-9' | fold -w 32 | head -n 1 > /app/git_hash
echo "myhostname = ${POSTFIX_MAIL_HOST}" >> /etc/postfix/main.cf
echo "relayhost = ${POSTFIX_RELAY_HOST}" >> /etc/postfix/main.cf

service cron start &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start cron: $status"
  exit $status
fi


service syslog-ng start &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start syslog-ng: $status"
  exit $status
fi


service postfix start &
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start postfix: $status"
  exit $status
fi


# Start the second process
gunicorn statdev.wsgi --bind :8080 --config /app/gunicorn.ini
status=$?
if [ $status -ne 0 ]; then
  echo "Failed to start gunicorn: $status"
  exit $status
fi

