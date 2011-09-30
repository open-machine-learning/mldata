from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseRedirect
from repository.models.data import Data
from repository.models.challenge import Challenge
from repository.models.task import Task

def about_videos(request, video=None, template='about/videos.html', extra_context={}):
    """
        View displays main information about challenge
    """
    VIDEOS = ['VlxWhDj3OkQ',
              'zY0UhXPy8fM',
              '_tKAXwsPDqQ',
              'V7AKtbchDtI',
              'UIIg9uF7Ic0']
    
    
    return render_to_response(template,
                              RequestContext(request,dict(extra_context.items() + {'video': VIDEOS[int(video)]}.items())))
