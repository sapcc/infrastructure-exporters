#!/usr/bin/dumb-init /bin/sh


# If user does not supply config file or type, use the default
if [ "$1" = "cmd.py" ]; then
    if [[ ! echo $@ | grep ' \-c' ] && [ ! echo $@ | grep ' \-f' ]]; then
       set -- "$@" -f $(pwd)/samples/apicconfig.yaml
       set -- "$@" -t apicexporter
    fi
fi

exec pipenv run python ./cmd.py "$@"
