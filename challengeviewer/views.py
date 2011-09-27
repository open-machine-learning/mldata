"""
View for datacite application. Display metadata about dataset
in the xml format.
"""
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect
from repository.models.data import Data
from repository.models.challenge import Challenge

def challengeviewer_index(request, slug):
    """
        View displays main information about challenge
    """
    challenge = Challenge.get_object(slug)
    
    return render_to_response('challengeviewer/base.html',
                              {'challenge': challenge})

def challengeviewer_results(request, slug):
    """
        View displays main information about challenge
    """
    challenge = Challenge.get_object(slug)

    return render_to_response('challengeviewer/results.html',
                              {'challenge': challenge})

def challengeviewer_task(request, slug, task_slug):
    """
        View displays main information about challenge
    """
    challenge = Challenge.get_object(slug)

    return render_to_response('challengeviewer/task.html',
                              {'challenge': challenge})

def challengeviewer_submit(request, slug):
    """
        View displays main information about challenge
    """
    challenge = Challenge.get_object(slug)

    return render_to_response('challengeviewer/submit.html',
                              {'challenge': challenge})

def challengeviewer_login(request, slug):
    """
        View displays main information about challenge
    """
    challenge = Challenge.get_object(slug)

    return render_to_response('challengeviewer/login.html',
                              {'challenge': challenge})
