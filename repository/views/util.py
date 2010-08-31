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
