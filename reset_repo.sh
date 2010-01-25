#!/bin/sh

python manage.py reset repository comments tagging
python manage.py loaddata license tasktype toyrepo
