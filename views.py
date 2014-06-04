"""
View for the welcome page
"""
from django.shortcuts import render_to_response
from repository.models import Repository

def welcome(request):
    info_dict = {
        'request': request,
        'section': 'welcome',
        'recent': Repository.get_recent(request.user),
    }
    return render_to_response('welcome.html', info_dict)
