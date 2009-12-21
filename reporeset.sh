#!/bin/sh

./manage.py reset repository comments tagging
./manage.py loaddata license tasktype
