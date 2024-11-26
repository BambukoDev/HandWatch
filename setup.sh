#!/usr/bin/env bash
# Setup the project for a raw Pico W
cp -r lib/lcd /run/media/$USER/CIRCUITPY/lib
cp -r lib/pyRTOS /run/media/$USER/CIRCUITPY/lib

./upload.sh