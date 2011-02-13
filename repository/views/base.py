import sys
import datetime
import traceback
import os
import uuid
import cPickle as pickle
import time

from django.template import RequestContext
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

from preferences.models import Preferences
from repository.forms import *
from repository.models import *
from repository.views.util import get_versions_paginator, get_page, get_per_page
from repository.views.util import get_tag_clouds, sendfile
from settings import DATAPATH, CACHE_ROOT, MEDIA_ROOT
from tagging.models import Tag

MEGABYTE = 1048576

DOWNLOAD_WARNING_LIMIT = 30000 # 30k is this a good margin?

def _download_cleanup(fname_export):
    """ erase exported file """
    try:
        os.remove(fname_export)
    except:
        pass

def _response_for(request, klass, name, info_dict):
    return render_to_response(klass.__name__.lower() + '/' + name + '.html', info_dict,
            context_instance=RequestContext(request))

@transaction.commit_on_success
def activate(request, klass, id):
    """Activate item given by id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
    @param id: id of the item to activate
    @type id: integer
    @return: redirect user to login page or item's page
    @rtype: Django response
    @raise Http404: if item couldn't be found
    """
    if not request.user.is_authenticated():
        url = reverse(klass.__name__.lower() + '_activate', args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = klass.get_object(id)
    if not obj: raise Http404
    if not obj.can_activate(request.user):
        return HttpResponseForbidden()

    obj.is_public = True
    obj.save()
    obj.current=klass.set_current(obj)
    obj.save()

    return HttpResponseRedirect(obj.get_absolute_slugurl())

@transaction.commit_on_success
def delete(request, klass, id):
    """Delete item given by id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
    @param id: id of the item to delete
    @type id: integer
    @return: redirect user to login page or item's page or user's my page
    @rtype: Django response
    @raise Http404: if item couldn't be found
    """
    if not request.user.is_authenticated():
        url = reverse(klass.__name__.lower() + '_delete', args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = klass.get_object(id)
    if not obj: raise Http404
    if not obj.can_delete(request.user):
        return HttpResponseForbidden()

    obj.is_deleted = True
    obj.save(silent_update=True)

    current = klass.set_current(obj)
    if current:
        return HttpResponseRedirect(current.get_absolute_slugurl())

    return HttpResponseRedirect(reverse(klass.__name__.lower() + '_my'))

def download(request, klass, slug, type='plain'):
    """Download file relating to item given by id and klass and possibly type.

    @param request: request data
    @type request: Django request
    @param klass: item's class
    @type klass: either Data, Task or Method
    @param slug: slug of item to downlaod
    @type slug: string
    @return: download file response
    @rtype: Django response
    @raise Http404: if item couldn't be retrieved or given klass is unexpected or file doesn't exist or a conversion error occurred
    """
    if not klass in (Data, Task):
        raise Http404

    obj = klass.get_object(slug)
    if not obj: raise Http404
    if not obj.file:
        raise Http404
    if not obj.can_download(request.user):
        return HttpResponseForbidden()

    fname_export = None
    fileobj = obj.file
    fname = os.path.join(MEDIA_ROOT, obj.file.name)
    format = ml2h5.fileformat.get(fname)

    if type == 'plain':
        if format == 'h5':
            ctype = 'application/x-hdf'
        else:
            ctype = 'application/octet-stream'
    else:
        if format != 'h5': # only convert h5 files
            raise Http404

        if type!='xml' and not ml2h5.fileformat.can_convert_h5_to(type, fname):
            raise Http404

        prefix, dummy = os.path.splitext(os.path.basename(obj.file.name))
        # create unique export filename
        fname_export = os.path.join(CACHE_ROOT, prefix + '_' + repr(time.time()).replace('.','') + '.' + type)
        # create humanly readable export filename
        if type == 'matlab':
            fname_export_visible = os.path.join(CACHE_ROOT, prefix + '.mat')
        elif type == 'rdata':
            fname_export_visible = os.path.join(CACHE_ROOT, prefix + '.RData')
        else:
            fname_export_visible = os.path.join(CACHE_ROOT, prefix + '.' + type)

        if type in ('xml', 'csv', 'arff', 'libsvm', 'matlab', 'octave', 'rdata'):
            try:
                c = ml2h5.converter.Converter(fname, fname_export, format_out=type)
                c.run()
            except ml2h5.converter.ConversionError, e:
                subject = 'Download: Failed conversion of %s to %s' % (fname, type)
                body = traceback.format_exc() + "\n" + str(e)
                mail_admins(subject, body)
                _download_cleanup(fname_export)
                raise Http404
        else:
            raise Http404

        if type == 'matlab':
            ctype = 'application/x-matlab'
        else:
            ctype = 'application/' + type
        fileobj = File(open(fname_export, 'r'))
        fileobj.name=fname_export_visible # use humanly readable name

    response = sendfile(fileobj, ctype)
    _download_cleanup(fname_export)
    obj.increase_downloads()
    return response

@transaction.commit_on_success
def view(request, klass, slug_or_id, version=None):
    """View item given by slug and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
    @param slug_or_id: slug or id of the item to view
    @type slug_or_id: string or integer
    @return: view page or review page if klass Data and item not approved
    @rtype: Django response
    @raise Http404: if item couldn't be found
    """
    kname=klass.__name__.lower()
    obj = klass.get_object(slug_or_id, version)
    if not obj: raise Http404
    if not obj.can_view(request.user):
        return HttpResponseForbidden()
    if not obj.check_is_approved():
        return HttpResponseRedirect(reverse(kname + '_review', args=[obj.slug]))

    current = obj.update_current_hits()

    # need tags in list
    versions = get_versions_paginator(request, obj)

    info_dict = {
        'object': obj,
        'request': request,
        'can_edit': obj.can_edit(request.user),
        'can_activate': obj.can_activate(request.user),
        'can_delete': obj.can_delete(request.user),
        'dependent_entries_exist': obj.dependent_entries_exist(),
        'dependent_link': '',
        'current': current,
        'rating_form': RatingForm.get(request, obj),
        'tagcloud': get_tag_clouds(request),
        'download_warning_limit': DOWNLOAD_WARNING_LIMIT,
        kname : True,
        'klass': klass.__name__,
        'section': 'repository',
        'versions': versions,
    }
    if request.method == 'GET' and 'c' in request.GET:
        info_dict['show_comments'] = True

    if klass == Data:
        tasks=obj.get_related_tasks(request.user)
        PER_PAGE = get_per_page(tasks.count())
        info_dict['page']=get_page(request, tasks, PER_PAGE)
        info_dict['per_page']=PER_PAGE
        info_dict['related_tasks']=tasks
        info_dict['dependent_link']='#tabs-method'
    else:
        if request.user.is_authenticated():
            if request.method == 'POST':
                form = ResultForm(request.POST, request.FILES, request=request)
                if form.is_valid():
                    new = form.save(commit=False)
                    r=Result.objects.filter(method=new.method, task=new.task, challenge=new.challenge)
                    if r.count():
                        new=r[0]

                    new.aggregation_score=-1
                    new.output_file = request.FILES['output_file']
                    score, msg, ok = new.predict()
                    try:
                        new.aggregation_score=score[0]
                        new.complex_result_type=score[1]
                        new.complex_result=pickle.dumps(score[2])
                    except Exception:
                        new.aggregation_score=score

                    if ok:
                        new.save()
                    else:
                        form.errors['output_file'] = ErrorDict({'': msg}).as_ul()
            else:
                form = ResultForm(request=request)

            info_dict['result_form'] = form


        if klass == Task:
            objects=Result.objects.filter(task=obj)
            if request.user.is_authenticated():
                form.fields['task'].queryset = obj
                form.fields['challenge'].queryset = obj.get_challenges()
            PER_PAGE = get_per_page(objects.count())
            info_dict['page']=get_page(request, objects, PER_PAGE)
            info_dict['per_page']=PER_PAGE
            info_dict['data']=obj.get_data()
            info_dict['dependent_link']='foo'

        elif klass == Method:
            objects=Result.objects.filter(method=obj)
            PER_PAGE = get_per_page(objects.count())
            info_dict['page']=get_page(request, objects, PER_PAGE)
            info_dict['per_page']=PER_PAGE

        elif klass == Challenge:
            t=obj.get_tasks()
            if request.user.is_authenticated():
                form.fields['task'].queryset = t
                form.fields['challenge'] = obj
            info_dict['tasks']=t
            objects=Result.objects.filter(challenge=obj).order_by('task__name','aggregation_score')
            PER_PAGE = get_per_page(objects.count())
            info_dict['page']=get_page(request, objects, PER_PAGE)
            info_dict['per_page']=PER_PAGE


    if hasattr(obj, 'data_heldback') and obj.data_heldback:
        info_dict['can_view_heldback'] = obj.data_heldback.can_view(request.user)
    info_dict['extract'] = obj.get_extract()
    return _response_for(request, klass, 'item_view', info_dict)


@transaction.commit_on_success
def new(request, klass, default_arg=None):
    """Create a new item of given klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
    @return: user login page, item's view page or this page again on failed form validation
    @rtype: Django response
    @raise Http404: if given klass is unexpected
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + request.path)

    upload_limit = Preferences.objects.get(pk=1).max_data_size
    formfunc = eval(klass.__name__ + 'Form')
    if request.method == 'POST':
        form = formfunc(request.POST, request.FILES, request=request)

        # manual validation coz it's required for new, but not edited Data
        if not request.FILES and klass == Data:
            form.errors['file'] = ErrorDict({'': _('This field is required.')}).as_ul()

        # check whether file is too large
        if klass in (Data, Task) and 'file' in request.FILES:
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
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    taskinfo = {
                        'train_idx': (form.cleaned_data['train_idx']),
                        'val_idx': (form.cleaned_data['val_idx']),
                        'test_idx': (form.cleaned_data['test_idx']),
                        'input_variables': form.cleaned_data['input_variables'],
                        'output_variables': form.cleaned_data['output_variables'],
                        'data_size': form.cleaned_data['data'].num_instances
                    }
                    new.file = None
                    if 'file' in request.FILES:
                        new.file = request.FILES['file']
                        new.save()
                        new.create_next_file(prev=None)
                    else:
                        new.save(taskinfo=taskinfo)
                elif klass == Method:
                    #if 'score' in request.FILES:
                    #    new.score = request.FILES['score']
                    #    new.score.name = new.get_scorename()
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    new.save()
                elif klass == Challenge:
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    new.save()
                    new.task=form.cleaned_data['task']
                    new.save()
                else:
                    raise Http404
                return HttpResponseRedirect(new.get_absolute_slugurl())
    else:
        if default_arg:
            form = formfunc(request=request, default_arg=default_arg)
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

    return _response_for(request, klass, 'item_new', info_dict)

@transaction.commit_on_success
def edit(request, klass, id):
    """Edit existing item given by slug or id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
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
                next.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                taskinfo = {
                    'train_idx': form.cleaned_data['train_idx'],
                    'val_idx': form.cleaned_data['val_idx'],
                    'test_idx': form.cleaned_data['test_idx'],
                    'input_variables': form.cleaned_data['input_variables'],
                    'output_variables': form.cleaned_data['output_variables'],
                    'data_size': prev.data.num_instances
                }
                next.file = None
                if 'file' in request.FILES:
                    next.file = request.FILES['file']
                    next.save()
                    next.create_next_file(prev)
                else:
                    next.save(taskinfo=taskinfo)
            elif klass == Method:
                next.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                next.save()
            elif klass == Challenge:
                next.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                next.save()
            else:
                raise Http404

            form.save_m2m() # for publications
            klass.set_current(next)
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
        'extract': prev.get_extract(),
    }
    return _response_for(request, klass, 'item_edit', info_dict)

@transaction.commit_on_success
def fork(request, klass, id):
    """Create a new item of given klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
    @return: user login page, item's view page or this page again on failed form validation
    @rtype: Django response
    @raise Http404: if given klass is unexpected
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + request.path)
    import pdb
    pdb.set_trace()
    prev = klass.get_object(id)
    if not prev: raise Http404
    if not prev.can_fork(request.user):
        return HttpResponseForbidden()
    prev.klass = klass.__name__
    prev.name+=' (forked)'

    upload_limit = Preferences.objects.get(pk=1).max_data_size
    formfunc = eval(klass.__name__ + 'Form')
    if request.method == 'POST':
        form = formfunc(request.POST, request.FILES, request=request)

        # manual validation coz it's required for new, but not edited Data
        if not request.FILES and klass == Data:
            form.errors['file'] = ErrorDict({'': _('This field is required.')}).as_ul()

        # check whether file is too large
        if klass in (Data, Task) and 'file' in request.FILES:
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
                    taskinfo = {
                        'train_idx': (form.cleaned_data['train_idx']),
                        'test_idx': (form.cleaned_data['test_idx']),
                        'input_variables': form.cleaned_data['input_variables'],
                        'output_variables': form.cleaned_data['output_variables']
                    }
                    new.file = None
                    if 'file' in request.FILES:
                        new.file = request.FILES['file']
                        new.save()
                        new.create_next_file(prev=None)
                    else:
                        new.save(taskinfo=taskinfo)
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    new.save(taskinfo=taskinfo)
                elif klass == Method:
                    #if 'score' in request.FILES:
                    #    new.score = request.FILES['score']
                    #    new.score.name = new.get_scorename()
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    new.save()
                elif klass == Challenge:
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    new.save()
                    new.task=form.cleaned_data['task']
                    new.save()
                else:
                    raise Http404
                return HttpResponseRedirect(new.get_absolute_slugurl())
    else:
        form = formfunc(request=request, instance=prev)

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

    return _response_for(request, klass, 'item_new', info_dict)

def index(request, klass, my=False, order_by='-pub_date', filter_type=None):
    """Index/My page for section given by klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
    @param my: if the page should be a My page or the archive index of the section
    @type my: boolean
    @return: section's index or My page
    @rtype: Django response
    """
    objects = klass.objects.filter(is_deleted=False)

    if klass == Task and filter_type:
        objects = objects.filter(type=filter_type)
        
    if klass == Data:
        objects = objects.filter(is_approved=True)

    if my and request.user.is_authenticated():
        objects = objects.filter(user=request.user, is_current=True)
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

    objects = objects.order_by(order_by, '-pub_date')


    kname=klass.__name__.lower()
    PER_PAGE = get_per_page(objects.count())
    info_dict = {
        'request': request,
        kname : get_page(request, objects, PER_PAGE),
        kname + '_per_page': PER_PAGE,
        'klass' : klass.__name__,
        'unapproved': unapproved,
        'my_or_archive': my_or_archive,
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
        'download_warning_limit': DOWNLOAD_WARNING_LIMIT,
        'yeah': 'index',
    }

    return render_to_response('repository/item_index.html',
            info_dict, context_instance=RequestContext(request))

def tags_view(request, tag, klass):
    """View all items tagged by given tag in given klass.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    @param klass: klass of tagged item
    @type klass: repository.Data/Task/Method
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

    PER_PAGE = get_per_page(len(objects))
    kname = klass.__name__.lower()

    info_dict = {
        'request': request,
        'tag': tag,
        'tagcloud': get_tag_clouds(request),
        kname : get_page(request, objects, PER_PAGE),
        'klass' : klass.__name__,
        kname + '_per_page': PER_PAGE,
        'download_warning_limit': DOWNLOAD_WARNING_LIMIT,
    }
    return render_to_response('repository/item_index.html', info_dict,
            context_instance=RequestContext(request))

def rate(request, klass, id):
    """Rate an item given by id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
    @param id: item's id
    @type id: integer
    @return: redirect to item's view page
    @rtype: Django response
    @raise Http404: if item could not be found
    """
    if not request.user.is_authenticated():
        url = reverse(klass.__name__.lower() + '_rate', args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

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
        'download_warning_limit': DOWNLOAD_WARNING_LIMIT,
        'yeah': 'main_index',
    }
    return render_to_response('repository/index.html', info_dict,
            context_instance=RequestContext(request))


def search(request):
    """Search the repository for given term.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    if request.method == 'GET' and 'searchterm' in request.GET:
        searchterm = request.GET['searchterm']

        classes=[]
        for c in (Data, Task, Method, Challenge):
            kname=c.__name__.lower()
            if kname in request.GET:
                classes.append(c)

        info_dict = {
            'request': request,
            'tagcloud': get_tag_clouds(request),
            'section': 'repository',
            'download_warning_limit': DOWNLOAD_WARNING_LIMIT,
            'yeah': 'search',
            'my_or_archive' : _('Search Results for "%s"' % searchterm)
        }

        for klass in classes:
            objects = klass.objects.filter(is_deleted=False, is_current=True, is_public=True)
            if klass == Data:
                objects = objects.filter(is_approved=True)

            searcherror = True

            if searchterm:
                info_dict['searchterm'] = searchterm
                objects = objects.filter(Q(name__icontains=searchterm) |
                        Q(summary__icontains=searchterm)).order_by('-pub_date')
                searcherror = objects.count()==0

            kname=klass.__name__.lower()
            PER_PAGE = get_per_page(objects.count())
            info_dict[kname]=get_page(request, objects, PER_PAGE)
            info_dict[kname + '_per_page']=PER_PAGE
            info_dict[kname + '_searcherror']=searcherror

        return render_to_response('repository/item_index.html', info_dict,
                context_instance=RequestContext(request))
    raise Http404
