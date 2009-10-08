"""
All custom repository logic is kept here
"""

from django.shortcuts import render_to_response
from repository.models import Data, Task, Solution

def index(request):
	return render_to_response('repository/index.html')


def data_index(request):
	return render_to_response('repository/data_index.html')

def data_new(request):
	return render_to_response('repository/data_new.html')


def task_index(request):
	return render_to_response('repository/task_index.html')

def task_new(request):
	return render_to_response('repository/task_new.html')


def solution_index(request):
	return render_to_response('repository/solution_index.html')

def solution_new(request):
	return render_to_response('repository/solution_new.html')


