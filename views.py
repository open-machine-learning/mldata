"""
View for the welcome page
"""
from django.shortcuts import render_to_response
from repository.models import Repository
from repository.util import get_recent

def welcome(request):
    info_dict = {
        'request': request,
        'section': 'welcome',
        'recent': get_recent(Repository, request.user),
    }
    return render_to_response('welcome.html', info_dict)
