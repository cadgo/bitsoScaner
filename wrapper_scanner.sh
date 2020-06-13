#!/bin/bash
#monitorear con monit
PIDFILE=/var/run/bitsoscaner

case $1 in
   start)
       # Launch your program as a detached process
       python3 /home/carlos_diaz_s3c/apps/django/django_projects/venv/bitsoScanerV3/scanner.py cadgo@hotmail.com 2>/dev/null &
       # Get its PID and store it
       echo $! > ${PIDFILE} 
   ;;
   stop)
      kill `cat ${PIDFILE}`
      # Now that it's killed, don't forget to remove the PID file
      rm ${PIDFILE}
   ;;
   *)
      echo "usage: wrapper_scanner.sh {start|stop}" ;;
esac
exit 0
