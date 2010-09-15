import sys

import datetime
from django.core import serializers
from django.core.cache import cache
from django.core.files import File
from django.core.mail import mail_admins
from django.core.paginator import EmptyPage
from django.core.paginator import InvalidPage
from django.core.paginator import Paginator
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.db import transaction
from django.db.models import Q
from django.forms.util import ErrorDict
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.http import HttpResponseServerError
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.utils import simplejson
from django.utils.translation import ugettext as _
import ml2h5.converter
import ml2h5.data
import ml2h5.fileformat
import ml2h5.task
import os
from preferences.models import Preferences
from repository.forms import *
from repository.models import *
import repository.util as util
from settings import DATAPATH
from settings import MEDIA_ROOT
from settings import TAG_SPLITSTR
import subprocess
from tagging.models import Tag
import traceback
from utils.uploadprogresscachedhandler import UploadProgressCachedHandler
import uuid

from repository.views.util import *

from repository.views.url_helper import UrlHelper

def response_for(klass, name, info_dict):
    return render_to_response(klass.__name__.lower() + '/' + name + '.html', info_dict)
    

@transaction.commit_on_success
def activate(request, klass, id):
    """Activate item given by id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param id: id of the item to activate
    @type id: integer
    @return: redirect user to login page or item's page
    @rtype: Django response
    @raise Http404: if item couldn't be found
    """
    if not request.user.is_authenticated():
        func = eval(klass.__name__.lower() + '_activate')
        url = reverse(func, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = klass.get_object(id)
    if not obj: raise Http404
    if obj.can_activate(request.user):
        obj.is_public = True
        obj.save()
        klass.set_current(obj.slug)

    return HttpResponseRedirect(obj.get_absolute_slugurl())

@transaction.commit_on_success
def delete(request, klass, id):
    """Delete item given by id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param id: id of the item to delete
    @type id: integer
    @return: redirect user to login page or item's page or user's my page
    @rtype: Django response
    @raise Http404: if item couldn't be found
    """
    if not request.user.is_authenticated():
        func = eval(klass.__name__.lower() + '_delete')
        url = reverse(func, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = klass.get_object(id)
    if not obj: raise Http404
    if not obj.can_delete(request.user):
        return HttpResponseForbidden()
    obj.is_deleted = True
    obj.save()

    current = klass.set_current(obj.slug)
    if current:
        return HttpResponseRedirect(current.get_absolute_slugurl())

    func = eval(klass.__name__.lower() + '_my')
    return HttpResponseRedirect(reverse(func))

def download(request, klass, slug, type='plain'):
    """Download file relating to item given by id and klass and possibly type.

    @param request: request data
    @type request: Django request
    @param klass: item's class
    @type klass: either Data, Task or Solution
    @param slug: slug of item to downlaod
    @type slug: string
    @return: download file response
    @rtype: Django response
    @raise Http404: if item couldn't be retrieved or given klass is unexpected or file doesn't exist or a conversion error occurred
    """
    obj = klass.get_object(slug)
    if not obj: raise Http404
    if not obj.can_download(request.user):
        return HttpResponseForbidden()

    fname_export = None
    if klass == Data or klass == Task:
        fileobj = obj.file
        fname = obj.file.name
    elif klass == Solution:
        fileobj = obj.score
        fname = obj.score.name
    else:
        raise Http404
    format = ml2h5.fileformat.get(os.path.join(MEDIA_ROOT, fname))

    if type == 'plain':
        if format == 'h5':
            ctype = 'application/x-hdf'
        else:
            ctype = 'application/octet-stream'

    else:
        if not fileobj: # maybe no file attached to this item
            raise Http404
        if format != 'h5': # only convert h5 files
            raise Http404
        fname_h5 = os.path.join(MEDIA_ROOT, obj.file.name)
        fname_export = fname_h5 + '.' + type

        if type == 'xml':
            if not os.path.exists(fname_export) or _is_newer(fname_export, fname_h5):
                cmd = 'h5dump --xml ' + fname_h5 + ' > ' + fname_export
                if not subprocess.call(cmd, shell=True) == 0:
                    mail_admins('Download: Failed conversion of %s to XML' % (fname_h5), cmd)
                    raise Http404
        elif type in ('csv', 'arff', 'libsvm', 'matlab', 'octave'):
            if not os.path.exists(fname_export) or _is_newer(fname_export, fname_h5):
                try:
                    c = ml2h5.converter.Converter(fname_h5, fname_export, format_out=type)
                    c.run()
                except ml2h5.converter.ConversionError, e:
                    subject = 'Download: Failed conversion of %s to %s' % (fname_h5, type)
                    body = traceback.format_exc() + "\n" + str(e)
                    mail_admins(subject, body)
                    raise Http404
        else:
            raise Http404

        if type == 'matlab':
            ctype = 'application/x-matlab'
        else:
            ctype = 'application/' + type
        fileobj = File(open(fname_export, 'r'))

    if not fileobj: # something went wrong
        raise Http404

    response = sendfile(fileobj, ctype)

    fileobj.close()
    if fname_export: # remove exported file
        os.remove(fname_export)
    obj.increase_downloads()
    return response

def view(request, klass, slug_or_id, version=None):
    """View item given by slug and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param slug_or_id: slug or id of the item to view
    @type slug_or_id: string or integer
    @return: view page or review page if klass Data and item not approved
    @rtype: Django response
    @raise Http404: if item couldn't be found
    """
    obj = klass.get_object(slug_or_id, version)
    if not obj: raise Http404
    if not obj.can_view(request.user):
        return HttpResponseForbidden()
    if not obj.check_is_approved():
        return HttpResponseRedirect(reverse('repository.views.data.new_review', args=[obj.slug]))

    current = obj.update_current_hits()

    # need tags in list
    tags = obj.tags.split(TAG_SPLITSTR)
    versions = get_versions_paginator(request, obj)
    urls = UrlHelper(obj, obj.id)

    # klass-specific
    obj.check_has_h5()

    info_dict = {
        'object': obj,
        'request': request,
        'can_activate': obj.can_activate(request.user),
        'can_delete': obj.can_delete(request.user),
        'current': current,
        'rating_form': RatingForm.get(request, obj),
        'tagcloud': get_tag_clouds(request),
        'related': obj.filter_related(request.user),
        'klass': klass.__name__,
        'section': 'repository',
        'tags': tags,
        'versions': versions,
        'urls': urls,
        'data': obj.get_related_data()
    }

    if hasattr(obj, 'data_heldback') and obj.data_heldback:
        info_dict['can_view_heldback'] = obj.data_heldback.can_view(request.user)

    info_dict['extract'] = obj.get_extract()

    return response_for(klass, 'item_view', info_dict)


@transaction.commit_on_success
def new(request, klass):
    """Create a new item of given klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: user login page, item's view page or this page again on failed form validation
    @rtype: Django response
    @raise Http404: if given klass is unexpected
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + request.path)

    upload_limit = Preferences.objects.get(pk=1).max_data_size
    formfunc = eval(klass.__name__ + 'Form')
    if request.method == 'POST':
        request.upload_handlers.insert(0,
            UploadProgressCachedHandler(request=request))
        form = formfunc(request.POST, request.FILES, request=request)

        # manual validation coz it's required for new, but not edited Data
        if not request.FILES and klass == Data:
            form.errors['file'] = ErrorDict({'': _('This field is required.')}).as_ul()

        # check whether file is too large
        if klass == Data:
            if len(request.FILES['file']) > upload_limit:
                form.errors['file'] = ErrorDict({'': _('File is too large!  Must be smaller than %dMB!' % (upload_limit / MEGABYTE))}).as_ul()

        if form.is_valid():
            new = form.save(commit=False)
            new.pub_date = datetime.datetime.now()
            try:
                new.slug = new.make_slug()
            except IntegrityError:
                # looks quirky...
                d = ErrorDict({'':
                    _('The given name yields an already existing slug. Please try another name.')})
                form.errors['name'] = d.as_ul()
            else:
                new.version = 1
                new.is_current = True
                new.is_public = False
                new.user = request.user

                if not form.cleaned_data['keep_private']:
                    new.is_public = True

                if klass == Data:
                    new.file = request.FILES['file']
                    new.num_instances = -1
                    new.num_attributes = -1
                    new.save()

                    # InMemoryUploadedFile returns file-like object whereas
                    # zipfile/tarfile modules used in get_uncompressed() require
                    # filename (prior to python 2.7), so we have to save it to
                    # disk, then rename, then save object again.
                    name_old = os.path.join(MEDIA_ROOT, new.file.name)
                    uncompressed = ml2h5.data.get_uncompressed(name_old)
                    if uncompressed:
                        os.remove(name_old)
                        name_old = uncompressed

                    new.format = ml2h5.fileformat.get(name_old)
                    name_new = os.path.join(DATAPATH, new.get_filename())
                    os.rename(name_old, os.path.join(MEDIA_ROOT, name_new))
                    new.file.name = name_new
                    new.save()
                elif klass == Task:
                    if 'file' in request.FILES:
                        new.file = request.FILES['file']
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    taskfile = {
                        'train_idx': form.cleaned_data['train_idx'],
                        'test_idx': form.cleaned_data['test_idx'],
                        'input_variables': form.cleaned_data['input_variables'],
                        'output_variables': form.cleaned_data['output_variables']
                    }
                    new.save(update_file=True, taskfile=taskfile)
                elif klass == Solution:
                    if 'score' in request.FILES:
                        new.score = request.FILES['score']
                        new.score.name = new.get_scorename()
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                else:
                    raise Http404
                return HttpResponseRedirect(new.get_absolute_slugurl())
    else:
        form = formfunc(request=request)

    info_dict = {
        'klass': klass.__name__,
        'uuid': uuid.uuid4(), # for upload progress bar
        'url_new': request.path,
        'form': form,
        'request': request,
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
        'upload_limit': "%dMB" % (upload_limit / MEGABYTE)
    }

    if klass == Data:
        return render_to_response('data/item_new.html', info_dict)
    elif klass == Task:
        return render_to_response('task/item_new.html', info_dict)
    elif klass == Solution:
        return render_to_response('solutions/item_new.html', info_dict)


@transaction.commit_on_success
def edit(request, klass, id):
    """Edit existing item given by slug or id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param id: id of the item to activate
    @type id: integer
    @return: user login page, item's view page or this page again on failed form validation
    @rtype: Django response
    @raise Http404: if item couldn't be found or given klass is unexpected
    """
    prev = klass.get_object(id)
    if not prev: raise Http404
    prev.klass = klass.__name__
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + request.path)
    if not prev.can_edit(request.user):
        return HttpResponseForbidden()

    formfunc = eval(klass.__name__ + 'Form')
    if request.method == 'POST':
        request.POST['name'] = prev.name # cheat a little
        form = formfunc(request.POST, request=request)

        if form.is_valid():
            next = form.save(commit=False)
            next.pub_date = datetime.datetime.now()
            next.slug = prev.slug
            next.version = next.get_next_version()
            next.user = request.user

            if prev.is_public: # once public, always public
                next.is_public = True
            elif not form.cleaned_data['keep_private']:
                next.is_public = True

            if klass == Data:
                next.format = prev.format
                next.is_approved = prev.is_approved
                next.file = prev.file
                next.save()
            elif klass == Task:
                if 'file' in request.FILES:
                    next.file = request.FILES['file']
                    next.file.name = next.get_filename()
                    filename = os.path.join(MEDIA_ROOT, prev.file.name)
                    if os.path.isfile(filename):
                        os.remove(filename)
                else:
                    next.file = prev.file

                next.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                taskfile = {
                    'train_idx': form.cleaned_data['train_idx'],
                    'test_idx': form.cleaned_data['test_idx'],
                    'input_variables': form.cleaned_data['input_variables'],
                    'output_variables': form.cleaned_data['output_variables']
                }
                next.save(update_file=True, taskfile=taskfile)
            elif klass == Solution:
                if 'score' in request.FILES:
                    next.score = request.FILES['score']
                    next.score.name = next.get_scorename()
                    filename = os.path.join(MEDIA_ROOT, prev.score.name)
                    if os.path.isfile(filename):
                        os.remove(filename)
                else:
                    next.score = prev.score
                next.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                next.save()
            else:
                raise Http404

            form.save_m2m() # for publications
            klass.set_current(next.slug)
            return HttpResponseRedirect(next.get_absolute_slugurl())
    else:
        form = formfunc(instance=prev, request=request)
        if klass == Task:
            form.prefill(os.path.join(MEDIA_ROOT, prev.file.name))

    info_dict = {
        'form': form,
        'object': prev,
        'request': request,
        'publication_form': PublicationForm(),
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
    }

    if klass == Data:
        return render_to_response('data/item_edit.html', info_dict)
    elif klass == Task:
        return render_to_response('task/item_edit.html', info_dict)
    elif klass == Solution:
        return render_to_response('solution/item_edit.html', info_dict)

def index(request, klass, my=False, searchterm=None):
    """Index/My page for section given by klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param my: if the page should be a My page or the archive index of the section
    @type my: boolean
    @param searchterm: search term to reduce queryset
    @type searchterm: string
    @return: section's index or My page
    @rtype: Django response
    """
    objects = klass.objects.filter(is_deleted=False).order_by('-pub_date')
    if klass == Data:
        objects = objects.filter(is_approved=True)

    if my and request.user.is_authenticated():
        objects = objects.filter(user=request.user, is_current=True).order_by('slug')
        if klass == Data:
            unapproved = klass.objects.filter(
                user=request.user, is_approved=False
            )
        else:
            unapproved = None
        my_or_archive = _('My')
    else:
        objects = objects.filter(is_current=True, is_public=True)
        unapproved = None
        my_or_archive = _('Public Archive')

    searcherror = False
    if searchterm:
        objects, searcherror = klass.search(objects, searchterm)

    PER_PAGE = get_per_page(objects.count())
    info_dict = {
        'request': request,
        'page': get_page(request, objects, PER_PAGE),
        'searcherror': searcherror,
        'klass': klass.__name__,
        'unapproved': unapproved,
        'my_or_archive': my_or_archive,
        'per_page': PER_PAGE,
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
    }
    if searchterm:
        info_dict['searchterm'] = searchterm

    if klass == Data:
        return render_to_response('data/item_index.html', info_dict)
    elif klass == Task:
        return render_to_response('task/item_index.html', info_dict)
    elif klass == Solution:
        return render_to_response('solution/item_index.html', info_dict)

def tags_view(request, tag, klass):
    """View all items tagged by given tag in given klass.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    @param klass: klass of tagged item
    @type klass: repository.Data/Task/Solution
    @return: rendered response page
    @rtype: Django response
    @raise Http404: if tag doesn't exist or no items are tagged by given tag
    """
    try:
        tag = Tag.objects.get(name=tag)
        objects = klass.get_current_tagged_items(request.user, tag)
        if not objects: raise Http404
    except Tag.DoesNotExist:
        raise Http404

    info_dict = {
        'request': request,
        'section': 'repository',
        'klass': klass.__name__,
        'tag': tag,
        'tagcloud': get_tag_clouds(request),
        'objects': objects,
    }
    if klass == Data:
        return render_to_response('data/tags_view.html', info_dict)
    elif klass == Task:
        return render_to_response('task/tags_view.html', info_dict)
    elif klass == Solution:
        return render_to_response('solutions/tags_view.html', info_dict)

def rate(request, klass, id):
    """Rate an item given by id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param id: item's id
    @type id: integer
    @return: redirect to item's view page
    @rtype: Django response
    @raise Http404: if item could not be found
    """
    if not request.user.is_authenticated():
        next = '?next=' + reverse(eval(klass.__name__.lower() + '_rate'), args=[id])
        return HttpResponseRedirect(reverse('user_signin') + next)

    obj = klass.get_object(id)
    if not obj: raise Http404
    rklass = eval(klass.__name__ + 'Rating')
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            r, fail = rklass.objects.get_or_create(user=request.user, repository=obj)
            r.update(form.cleaned_data['interest'], form.cleaned_data['doc'])

    return HttpResponseRedirect(obj.get_absolute_slugurl())

def main_index(request):
    """Index page of app repository.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    info_dict = {
        'request': request,
        'section': 'repository',
        'tagcloud': get_tag_clouds(request),
    }
    return render_to_response('repository/index.html', info_dict)


def search(request):
    """Search the repository for given term.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    if request.method == 'GET' and 'searchterm' in request.GET:
        searchterm = request.GET['searchterm']
        if 'data' in request.GET and not 'task' in request.GET:
            return index(request, Data, False, searchterm)
        elif 'task' in request.GET and not 'data' in request.GET:
            return index(request, Task, False, searchterm)
        else: # all
            return index(request, Repository, False, searchterm)
    else:
        return HttpResponseRedirect(reverse(index))
