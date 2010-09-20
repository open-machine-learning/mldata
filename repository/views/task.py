from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseForbidden, Http404

from repository.models import *
from repository.forms import *
from repository.views.util import *
import repository.views.base as base

def index(request):
    return base.index(request, Task)

def my(request):
    return base.index(request, Task, True)

def new(request):
    return base.new(request, Task)

def view(request, id, version=None):
    return base.view(request, Task, id)

def view_slug(request, slug_task, version=None):
    """View Task item by slug.
    """
    return base.view(request, Task, slug_task, version)

def edit(request, id):
    """Edit page of Task section.
    """
    return base.edit(request, Task, id)

def delete(request, id):
    """Delete of Task section.
    """
    return base.delete(request, Task, id)

def activate(request, id):
    """Activate of Task section.
    """
    return base.activate(request, Task, id)

def download(request, slug):
    """Download of Task section.
    """
    return base.download(request, Task, slug)


def predict(request, slug):
    """AJAX: Evaluate results for Task given by id.
    """
    obj = Task.get_object(slug)
    if not obj: raise Http404
    if not obj.can_view(request.user):
        return HttpResponseForbidden()

    if 'qqfile' in request.FILES: # non-XHR style
        indata = request.FILES['qqfile'].read()
    else:
        indata = request.raw_post_data
    score, success = obj.predict(indata)

    data = '{"score": "' + score + '", "success": "' + str(success) + '"}'
    return HttpResponse(data, mimetype='text/plain')


def rate(request, id):
    return base.rate(request, Task, id)

def tags_view(request, tag):
    """View all items by given tag in Task.
    """
    return base.tags_view(request, tag, Task)

def task_rate(request, id):
    return base.rate(request, Task, id)
