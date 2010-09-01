import datetime
import os
import sys
import subprocess
import uuid
import traceback
from django.core import serializers
from django.core.cache import cache
from django.core.files import File
from django.core.mail import mail_admins
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.servers.basehttp import FileWrapper
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.forms.util import ErrorDict
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, HttpResponseServerError, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.utils import simplejson
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from repository.models import *
from repository.forms import *
import repository.util as util

from settings import MEDIA_ROOT, TAG_SPLITSTR, DATAPATH
from preferences.models import Preferences
from tagging.models import Tag
import ml2h5.data
import ml2h5.task
import ml2h5.converter
import ml2h5.fileformat
from utils.uploadprogresscachedhandler import UploadProgressCachedHandler

NUM_HISTORY_PAGE = 20
NUM_PAGINATOR_RANGE = 10
PER_PAGE_INTS = [10, 20, 50, 100, 999999]
MEGABYTE = 1048576

def get_versions_paginator(request, obj):
    """Get a paginator for item versions.

    @param request: request data
    @type request: Django request
    @param obj: item to get versions for
    @type obj: either class Data, Task or Solution
    @return: paginator for item versions
    @rtype: Django paginator
    """
    items = obj.get_versions(request.user)
    paginator = Paginator(items, NUM_HISTORY_PAGE)

    try:
        # dunno a better way than looping thru, since index != obj.version
        index = 0
        for v in items:
            if v.id == obj.id:
                break
            else:
                index += 1
        default_page = (index / NUM_HISTORY_PAGE) + 1
        page = int(request.GET.get('page', str(default_page)))
    except ValueError:
        page = 1
    try:
        versions = paginator.page(page)
    except (EmptyPage, InvalidPage):
        versions = paginator.page(paginator.num_pages)

    return versions


def get_tag_clouds(request):
    """Convenience function to retrieve tag clouds for all item types.

    @param request: request data
    @type request: Django request
    @return: list of tags with attributes font_size
    @rtype: hash with keys 'Data', 'Task', 'Solution' containing lists of tagging.Tag
    """
    clouds = { 'Data': None, 'Task': None, 'Solution': None }
    for k in clouds.iterkeys():
        klass = eval(k)
        clouds[k] = util.get_tag_cloud(klass, request.user)
    return clouds

###############################################################################
#
# PAGINATION
#

def get_per_page(count):
    PER_PAGE=[ str(p) for p in PER_PAGE_INTS if p < count ]
    PER_PAGE.append(_('all'))
    return PER_PAGE

def get_page(request, objects, PER_PAGE):
    """Get paginator page for the given objects.

    @param request: request data
    @type request: Django request
    @param objects: objects to get page for
    @type objects: list of repository.Data/Task/Solution
    @return: a paginator page for the given objects
    @rtype: paginator.page
    """
    try:
        perpage = request.GET.get('pp', PER_PAGE[0])
    except ValueError:
        perpage = PER_PAGE[0]
    if perpage not in PER_PAGE:
        perpage = PER_PAGE[0]
    if perpage == 'all':
        l = len(objects)
        if l < 1:
            perpage = 1
        else:
            perpage = l
    paginator = Paginator(objects, int(perpage), allow_empty_first_page=True)

    try:
        num = int(request.GET.get('page', '1'))
    except ValueError:
        num = 1
    try:
        page = paginator.page(num)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)

    prev = page.number - (NUM_PAGINATOR_RANGE - 1)
    if prev > 0:
        page.prev = prev
    else:
        page.prev = False
        prev = 1

    next = page.number + (NUM_PAGINATOR_RANGE - 1)
    if next < paginator.num_pages:
        page.next = next
    else:
        page.next = False
        next = paginator.num_pages

    page.page_range = range(prev, page.number)
    page.page_range.extend(range(page.number, next + 1))
    page.first = 1
    page.last = paginator.num_pages
    page.perpage = perpage

    return page

def get_upload_limit():
    return Preferences.objects.get(pk=1).max_data_size

def redirect_to_signin(next_link, *args):
    return HttpResponseRedirect(reverse('user_signin') + "?next=" + reverse(next_link, args=args))

def sendfile(fileobj, ctype):
    """Send given file to client.

    @param fileobj: file to send
    @type fileobj: File
    @param ctype: content type of file
    @type ctype: string
    @return: response
    @rtype: HTTPResponse
    @raise: Http404 on OSError
    """
    # fails to work when OpenID Middleware is activated
#    filename = os.path.join(MEDIA_ROOT, fileobj.name)
#    wrapper = FileWrapper(file(filename))
#    response = HttpResponse(wrapper, content_type='application/octet-stream')
    # not sure if this alternative is a memory hog...
    response = HttpResponse()
    response['Content-Type'] = ctype
    try:
        response['Content-Length'] = fileobj.size
        response['Content-Disposition'] = 'attachment; filename=' +\
            fileobj.name.split(os.sep)[-1]
        for chunk in fileobj.chunks():
            response.write(chunk)
    except OSError, e: # something wrong with file, maybe not existing
        mail_admins('Failed sending of file', str(e))
        raise Http404

    return response
