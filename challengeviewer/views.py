"""
View for datacite application. Display metadata about dataset
in the xml format.
"""
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseRedirect
from repository.models.data import Data
from repository.models.challenge import Challenge
from repository.models.task import Task

def challengeviewer_index(request, slug):
    """
        View displays main information about challenge
    """
    challenge = Challenge.get_object(slug)
    
    return render_to_response('challengeviewer/index.html',
                              RequestContext(request,{'challenge': challenge}))

def challengeviewer_results(request, slug):
    """
        View displays results for given challenge
    """
    challenge = Challenge.get_object(slug)

    return render_to_response('challengeviewer/results.html',
                              RequestContext(request,{'challenge': challenge}))

def challengeviewer_task(request, slug, task_slug):
    """
        View displays task details
    """
    challenge = Challenge.get_object(slug)
    task = Task.get_object(task_slug)

    return render_to_response('challengeviewer/task.html',
                              RequestContext(request,{'challenge': challenge,
                               'task': task}))

def challengeviewer_submit(request, slug):
    """
        View allows user to submit results
    """
    challenge = Challenge.get_object(slug)
    
    from repository.views.base import handle_result_form
    form = handle_result_form(request)
    if form.added:
        return HttpResponseRedirect(reverse('challengeviewer_results', args=[slug]))

    return render_to_response('challengeviewer/submit.html',
                              RequestContext(request,{'challenge': challenge,
                                                      'form': form}))

def challengeviewer_login(request, slug):
    """
        View displays and handles login form
    """
    from django.contrib.auth import views as auth_views
    challenge = Challenge.get_object(slug)
    return auth_views.login(request, template_name='challengeviewer/login.html',
                            extra_context={'challenge': challenge, 'request': request})

def challengeviewer_logout(request, slug):
    """
        View logouts user from current request
    """
    from django.contrib.auth import logout
    logout(request)
    return HttpResponseRedirect(reverse('challengeviewer_index', args=[slug]))
