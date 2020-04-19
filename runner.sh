#!/bin/bash
ENV="/home/pi/gardenenv3.7"

source $ENV/bin/activate
cd /home/pi
python /home/pi/garden_scripts/sensor_logger.py

