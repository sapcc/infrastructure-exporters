#!/usr/bin/dumb-init /bin/sh


# Check if container was called without arguments
if [ "$#" -eq 0 ]; then
  exec pipenv run python ./cmd.py -f /usr/src/app/samples/apicconfig.yaml -t apichealth
fi
