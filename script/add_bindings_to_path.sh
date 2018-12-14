#!/bin/bash

home=`dirname $(readlink -e "$0")`

PROFILE_FILENAME="ms_sim.profile"

bindings_path=`readlink -f "$home/../stress-ng/bindings"`

echo "add $bindings_path to \$PATH? y/n ?"
read answer
if [ "$answer" == "y" ] ; then
	if [[ "$PATH" == *"$bindings_path"* ]]; then
		echo "Path already contains $bindings_path"
		exit 1	
	else
		echo "export PATH=$PATH:$bindings_path" >> "$PROFILE_FILENAME"
		echo "created $PROFILE_FILENAME file. Source file to add directory to path"
		exit 0
	fi
else
	echo "Not added to Path"
	exit 1
fi