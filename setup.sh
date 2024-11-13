#!/usr/bin/env bash
# Setup the project for a raw Pico W
cp lib/lcd /run/media/$USER/CIRCUITPY/lib
cp lib/pyRTOS /run/media/$USER/CIRCUITPY/pyRTOS

./upload.sh