"""
All custom repository logic is kept here
"""

from django.shortcuts import render_to_response
from repository.models import Data, Task, Solution

def index(request):
	return render_to_response('repository/index.html')

