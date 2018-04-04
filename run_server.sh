#!/bin/sh
sudo ionice -c 2 -n 0 nice -n -20 python3 main.py
