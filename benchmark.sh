#!/bin/bash

killall network_main.py

echo starting example server ...
time python3 network_main.py > /dev/null 2>&1 &
pid_server=$!
sleep 0.1

echo starting traffic generator ...
time python3 traffic_generator_main.py

echo stopping example server ...
kill -9 $pid_server


