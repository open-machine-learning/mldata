#!/bin/sh

python manage.py reset --noinput repository comments tagging
python manage.py loaddata license tasktype
