from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse

from repository.models import *
from repository.forms import *

from settings import TAG_SPLITSTR

import repository

from repository.views.util import *

def activate(request, id):
    pass

def edit(request, id):
    pass

def delete(request, id):
    pass

def view_slug(request, slug, version=None):
    return view(request, slug, version)

def view(request, slug_or_id, version=None):
    """View data item
    """
    print "hello!"

    obj = Data.get_object(slug_or_id, version)
    if not obj: raise Http404
    if not obj.can_view(request.user):
        return HttpResponseForbidden()

    if not obj.is_approved:
        return HttpResponseRedirect(reverse(data_new_review, args=[obj.slug]))

    current = Data.objects.get(slug=obj.slug, is_current=True)
    current.hits += 1
    current.save()

    tags = obj.tags.split(TAG_SPLITSTR)
    versions = get_versions_paginator(request, obj)
    url_activate = reverse(repository.views.data_activate, args=[obj.id])
    url_edit = reverse(repository.views.data_edit, args=[obj.id])
    url_delete = reverse(repository.views.data_delete, args=[obj.id])

    obj.has_h5()

    extract = obj.get_extract()

    info_dict = {
        'object': obj,
        'request': request,
        'can_activate': obj.can_activate(request.user),
        'can_delete': obj.can_delete(request.user),
        'current': current,
        'rating_form': RatingForm.get(request, obj),
        'tagcloud': get_tag_clouds(request),
        'related': obj.filter_related(request.user),
        'klass': Data,
        'section': 'repository',
        'extract': extract,
        'url_activate': url_activate,
        'url_edit': url_edit,
        'url_delete': url_delete,
        'tags': tags,
        'versions': versions
    }

    return render_to_response('data/item_view.html', info_dict)