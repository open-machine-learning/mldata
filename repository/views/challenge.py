from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseForbidden, Http404
from django.core import serializers

from repository.models import *
from repository.forms import *
from repository.views.util import *
import repository.views.base as base

def index(request, order_by='-pub_date'):
    """Index page of Challenge section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return base.index(request, Challenge, order_by=order_by)

def my(request):
    """My page of Challenge section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return base.index(request, Challenge, True)

def new(request):
    """New page of Challenge section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return base.new(request, Challenge)

def view(request, id):
    """View Challenge item by id.

    @param request: request data
    @type request: Django request
    @param id: id of item to view
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.view(request, Challenge, id)

def view_slug(request, slug_challenge, version=None):
    """View page of Challenge section.

    @param request: request data
    @type request: Django request
    @param version: version of item to view
    @type version: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.view(request, Challenge, slug_challenge, version)

def edit(request, id):
    """Edit page of Challenge section.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.edit(request, Challenge, id)

def activate(request, id):
    """Activate of Challenge section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to activate
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.activate(request, Challenge, id)

def delete(request, id):
    """Delete of Challenge section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to delete
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.delete(request, Challenge, id)


def tags_view(request, tag):
    """View all items by given tag in Challenge.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    """
    return base.tags_view(request, tag, Challenge)

def rate(request, id):
    return base.rate(request, Challenge, id)

def score_download(request, slug):
    """Download of Challenge section.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: rendered response page
    @rtype: Django response
    """
    return base.download(request, Challenge, slug)

def get_tasks(request, id):
    """AJAX: Get tasks associated to challenge that is specified by id.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: integer
    @return: tasks in response page
    @rtype: Django response
    """
    qs_task=Task().get_public_qs(request.user)

    try:
        tasks=Challenge.objects.get(pk=id).get_tasks()
    except Challenge.DoesNotExist:
        tasks=Task.objects.all()

    data = serializers.serialize('json', tasks, fields=('name'))
    tasks = [ t.repository_ptr for t in tasks ]
    data = serializers.serialize('json', tasks, fields=('name'))

    return HttpResponse(data, mimetype='text/plain')
