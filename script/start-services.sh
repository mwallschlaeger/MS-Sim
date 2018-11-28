#!/bin/bash

if [ "$(id -u)" != "0" ]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

home=`dirname $(readlink -e "$0")`
source "$home/services.sh"

for i in "$services" ; do
	service "$i" start
done

exit 0
