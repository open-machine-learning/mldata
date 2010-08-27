#!/usr/bin/env python

# args: taskfile datafile results

import ml2h5.task, ml2h5.data, sys, os

# adjust if you move this file elsewhere
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'mldata.settings'

from utils.performance_measure import *


fname_task = sys.argv[1]
test_idx, output_variables = ml2h5.task.get_test_output(fname_task)
print 'test_idx', test_idx
print 'output_variables', output_variables
fname_data = sys.argv[2]
correct = ml2h5.data.get_correct(fname_data, test_idx, output_variables)
print 'correct', correct

data = open(sys.argv[3], 'r').read()
try:
    predicted = [float(d) for d in data.split("\n") if d]
except ValueError:
    predicted = [d for d in data.split("\n") if d]

print 'predicted', predicted

print 'errorrate', ClassificationErrorRate().run(correct, predicted)
