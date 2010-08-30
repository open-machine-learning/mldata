"""
Define the views of app Repository

@var NUM_HISTORY_PAGE: how many versions of an item will be shown on history page
@type NUM_HISTORY_PAGE: integer
@var NUM_INDEX_PAGE: how many items will be shown on index/my page
@type NUM_INDEX_PAGE: integer
"""

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
from repository.models import *
from repository.forms import *
from settings import MEDIA_ROOT, TAG_SPLITSTR
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


def _get_versions_paginator(request, obj):
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


def _get_tag_clouds(request):
    """Convenience function to retrieve tag clouds for all item types.

    @param request: request data
    @type request: Django request
    @return: list of tags with attributes font_size
    @rtype: hash with keys 'Data', 'Task', 'Solution' containing lists of tagging.Tag
    """
    clouds = { 'Data': None, 'Task': None, 'Solution': None }
    for k in clouds.iterkeys():
        klass = eval(k)
        clouds[k] = klass.get_tag_cloud(request.user)
    return clouds


@transaction.commit_on_success
def _activate(request, klass, id):
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
def _delete(request, klass, id):
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




def _sendfile(fileobj, ctype):
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


def _is_newer(first, second):
    """Check if second given file is newer than first given file.

    @param first: name of first file
    @type first: string
    @param second: name of second file
    @type second: string
    """
    stats_first = os.stat(first)
    stats_second = os.stat(second)
    # index 8 is last modified
    if stats_second[8] > stats_first[8]:
        return True
    else:
        return False


def _download(request, klass, slug, type='plain'):
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

    response = _sendfile(fileobj, ctype)

    fileobj.close()
    if fname_export: # remove exported file
        os.remove(fname_export)
    obj.increase_downloads()
    return response


def data_download_xml(request, slug):
    """Download XML file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: download XML file response
    @rtype: Django response
    """
    return _download(request, Data, slug, 'xml')


def data_download_csv(request, slug):
    """Download CSV file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: download CSV file response
    @rtype: Django response
    """
    return _download(request, Data, slug, 'csv')


def data_download_arff(request, slug):
    """Download ARFF file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: download ARFF file response
    @rtype: Django response
    """
    return _download(request, Data, slug, 'arff')


def data_download_libsvm(request, slug):
    """Download LibSVM file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: download LibSVM file response
    @rtype: Django response
    """
    return _download(request, Data, slug, 'libsvm')


def data_download_matlab(request, slug):
    """Download Matlab file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: download Matlab file response
    @rtype: Django response
    """
    return _download(request, Data, slug, 'matlab')


def data_download_octave(request, slug):
    """Download Octave file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: download Octave file response
    @rtype: Django response
    """
    return _download(request, Data, slug, 'octave')


def _view(request, klass, slug_or_id, version=None):
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
    if klass == Data and not obj.is_approved:
        return HttpResponseRedirect(reverse(data_new_review, args=[obj.slug]))

    current = klass.objects.get(slug=obj.slug, is_current=True)
    current.hits += 1
    current.save()

    obj.klass = klass.__name__
    # need tags in list
    obj.tags = obj.tags.split(TAG_SPLITSTR)
    obj.versions = _get_versions_paginator(request, obj)
    klassname = klass.__name__.lower()
    obj.url_activate = reverse(eval(klassname + '_activate'), args=[obj.id])
    obj.url_edit = reverse(eval(klassname + '_edit'), args=[obj.id])
    obj.url_delete = reverse(eval(klassname + '_delete'), args=[obj.id])

    # klass-specific
    if klass == Data:
        obj.has_h5 = False
        if ml2h5.fileformat.get(os.path.join(MEDIA_ROOT, obj.file.name)) == 'h5':
            obj.has_h5 = True
        if 'conversion_failed' in obj.tags:
            obj.conversion_failed = True
    elif klass == Task:
        obj.d = obj.data
    elif klass == Solution:
        obj.d = obj.task.data

    info_dict = {
        'object': obj,
        'request': request,
        'can_activate': obj.can_activate(request.user),
        'can_delete': obj.can_delete(request.user),
        'current': current,
        'rating_form': RatingForm.get(request, obj),
        'tagcloud': _get_tag_clouds(request),
        'related': obj.filter_related(request.user),
        'klass': klass.__name__,
        'section': 'repository',
    }

    if hasattr(obj, 'data_heldback') and obj.data_heldback:
        info_dict['can_view_heldback'] = obj.data_heldback.can_view(request.user)

    if klass == Data:
        fname_h5 = os.path.join(MEDIA_ROOT, obj.file.name)
        try:
            info_dict['extract'] = ml2h5.data.get_extract(fname_h5)
        except Exception, e: # catch exceptions in general, but notify admins
            subject = 'Failed data extract of %s' % (fname_h5)
            body = "Hi Admin!" + "\n\n" + subject + ":\n\n" + str(e)
            mail_admins(subject, body)
            info_dict['extract'] = None
        return render_to_response('data/item_view.html', info_dict)

    elif klass == Task:
        fname_h5 = os.path.join(MEDIA_ROOT, obj.file.name)
        info_dict['extract'] = ml2h5.task.get_extract(fname_h5)
        return render_to_response('task/item_view.html', info_dict)



@transaction.commit_on_success
def _new(request, klass):
    """Create a new item of given klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: user login page, item's view page or this page again on failed form validation
    @rtype: Django response
    @raise Http404: if given klass is unexpected
    """
    url_new = reverse(eval(klass.__name__.lower() + '_new'))
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url_new)

    formfunc = eval(klass.__name__ + 'Form')
    upload_limit = Preferences.objects.get(pk=1).max_data_size
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
        'url_new': url_new,
        'form': form,
        'request': request,
        'tagcloud': _get_tag_clouds(request),
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
def _edit(request, klass, id):
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
    prev.url_edit = reverse(
        eval(klass.__name__.lower() + '_edit'), args=[prev.id])
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + prev.url_edit)
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
        'tagcloud': _get_tag_clouds(request),
        'section': 'repository',
    }

    if klass == Data:
        return render_to_response('data/item_edit.html', info_dict)
    elif klass == Task:
        return render_to_response('task/item_edit.html', info_dict)
    elif klass == Solution:
        return render_to_response('solution/item_edit.html', info_dict)


def _get_page(request, objects, PER_PAGE):
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


def _get_per_page(count):
    PER_PAGE=[ str(p) for p in PER_PAGE_INTS if p<count ]
    PER_PAGE.append(_('all'))
    return PER_PAGE


def _index(request, klass, my=False, searchterm=None):
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

    PER_PAGE = _get_per_page(objects.count())
    info_dict = {
        'request': request,
        'page': _get_page(request, objects, PER_PAGE),
        'searcherror': searcherror,
        'klass': klass.__name__,
        'unapproved': unapproved,
        'my_or_archive': my_or_archive,
        'per_page': PER_PAGE,
        'tagcloud': _get_tag_clouds(request),
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


def index(request):
    """Index page of app repository.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    info_dict = {
        'request': request,
        'section': 'repository',
        'tagcloud': _get_tag_clouds(request),
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
            return _index(request, Data, False, searchterm)
        elif 'task' in request.GET and not 'data' in request.GET:
            return _index(request, Task, False, searchterm)
        else: # all
            return _index(request, Repository, False, searchterm)
    else:
        return HttpResponseRedirect(reverse(index))


def data_index(request):
    """Index page of Data section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _index(request, Data)

def data_my(request):
    """My page of Data section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _index(request, Data, True)

def data_new(request):
    """New page of Data section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _new(request, Data)

def data_view(request, id):
    """View Data item by id.

    @param request: request data
    @type request: Django request
    @param id: id of item to view
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _view(request, Data, id)


def data_view_slug(request, slug, version=None):
    """View Data item by slug.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to view
    @type slug: string
    @param version: version of item to view
    @type version: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _view(request, Data, slug, version)

def data_edit(request, id):
    """Edit page of Data section.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: string or integer
    @return: rendered response page
    @rtype: Django response
    """
    return _edit(request, Data, id)

def data_delete(request, id):
    """Delete of Data section.

    @param request: request data
    @type request: Django request
    @param id: id of item to delete
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _delete(request, Data, id)

def data_activate(request, id):
    """Activate of Data section.

    @param request: request data
    @type request: Django request
    @param id: id of item to activate
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _activate(request, Data, id)

def data_download(request, slug):
    """Download of Data section.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: rendered response page
    @rtype: Django response
    """
    return _download(request, Data, slug)


def task_index(request):
    """Index page of Task section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _index(request, Task)

def task_my(request):
    """My page of Task section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _index(request, Task, True)

def task_new(request):
    """New page of Task section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _new(request, Task)

def task_view(request, id):
    """View Task item by id.

    @param request: request data
    @type request: Django request
    @param id: id of item to view
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _view(request, Task, id)

def task_view_slug(request, slug_data, slug_task, version=None):
    """View Task item by slug.

    @param request: request data
    @type request: Django request
    @param slug_data: data slug  of the item to view
    @type slug_data: string
    @param slug_task: task slug  of the item to view
    @type slug_task: string
    @param version: version of item to view
    @type version: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _view(request, Task, slug_task, version)

def task_edit(request, id):
    """Edit page of Task section.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _edit(request, Task, id)

def task_delete(request, id):
    """Delete of Task section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to delete
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _delete(request, Task, id)

def task_activate(request, id):
    """Activate of Task section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to activate
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _activate(request, Task, id)

def task_download(request, slug):
    """Download of Task section.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: rendered response page
    @rtype: Django response
    """
    return _download(request, Task, slug)


def task_predict(request, slug):
    """AJAX: Evaluate results for Task given by id.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: rendered response page
    @rtype: Django response
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




def solution_index(request):
    """Index page of Solution section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _index(request, Solution)

def solution_my(request):
    """My page of Solution section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _index(request, Solution, True)

def solution_new(request):
    """New page of Solution section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _new(request, Solution)

def solution_view(request, id):
    """View Solution item by id.

    @param request: request data
    @type request: Django request
    @param id: id of item to view
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _view(request, Solution, id)

def solution_view_slug(request, slug_data, slug_task, slug_solution, version=None):
    """View page of Solution section.

    @param request: request data
    @type request: Django request
    @param slug_data: data slug of the item to view
    @type slug_data: string
    @param slug_task: task slug of the item to view
    @type slug_task: string
    @param slug_solution: solution slug of the item to view
    @type slug_solution: string
    @param version: version of item to view
    @type version: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _view(request, Solution, slug_solution, version)

def solution_edit(request, id):
    """Edit page of Solution section.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _edit(request, Solution, id)

def solution_activate(request, id):
    """Activate of Solution section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to activate
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _activate(request, Solution, id)

def solution_delete(request, id):
    """Delete of Solution section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to delete
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _delete(request, Solution, id)

def score_download(request, slug):
    """Download of Solution section.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: rendered response page
    @rtype: Django response
    """
    return _download(request, Solution, slug)



@transaction.commit_on_success
def data_new_review(request, slug):
    """Review Data item to check if uploaded file is as expected.

    @param request: request data
    @type request: Django request
    @param slug: slug of the item to review
    @type slug: string
    @return: redirect user to login page or item's view page after approval or review form
    @rtype: Django response
    @raise Http404: if item couldn't be found
    """
    if not request.user.is_authenticated():
        next = '?next=' + reverse(data_new_review, args=[slug])
        return HttpResponseRedirect(reverse('user_signin') + next)

    obj = Data.get_object(slug)
    if not obj: raise Http404
    # don't want users to be able to remove items once approved
    if not obj.can_edit(request.user) or obj.is_approved:
        return HttpResponseForbidden()

    fname = os.path.join(MEDIA_ROOT, obj.file.name)
    form = None
    if request.method == 'POST':
        if request.POST.has_key('revert'):
            os.remove(fname)
            obj.delete()
            return HttpResponseRedirect(reverse(data_new))
        elif request.POST.has_key('approve'):
            form = DataReviewForm(request.POST)
            if form.is_valid():
                try:
                    obj.approve(fname, form.cleaned_data)
                except ml2h5.converter.ConversionError, error:
                    url = 'http://' + request.META['HTTP_HOST'] + reverse(
                        data_view_slug, args=[obj.slug])
                    subject = 'Failed conversion to HDF5: %s' % url
                    body = "Hi admin!\n\n" +\
                        'URL: ' + url + "\n\n" +\
                        traceback.format_exc() + "\n" + str(error)
                    mail_admins(subject, body)
                return HttpResponseRedirect(
                    reverse(data_view_slug, args=[obj.slug]))

    if not form:
        form = DataReviewForm()
        form.prefill(obj.format, ml2h5.fileformat.infer_seperator(fname))

    info_dict = {
        'object': obj,
        'form': form,
        'request': request,
        'tagcloud': _get_tag_clouds(request),
        'section': 'repository',
        'supported_formats': ', '.join(ml2h5.converter.HANDLERS.iterkeys()),
        'extract': ml2h5.data.get_extract(fname),
    }
    return render_to_response('data/data_new_review.html', info_dict)



def tags_data_view(request, tag):
    """View all items by given tag in Data.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    """
    return _tags_view(request, tag, Data)

def tags_task_view(request, tag):
    """View all items by given tag in Task.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    """
    return _tags_view(request, tag, Task)

def tags_solution_view(request, tag):
    """View all items by given tag in Solution.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    """
    return _tags_view(request, tag, Solution)

def _tags_view(request, tag, klass):
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
        'tagcloud': _get_tag_clouds(request),
        'objects': objects,
    }
    return render_to_response('repository/tags_view.html', info_dict)



def _rate(request, klass, id):
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


def data_rate(request, id):
    return _rate(request, Data, id)
def task_rate(request, id):
    return _rate(request, Task, id)
def solution_rate(request, id):
    return _rate(request, Solution, id)



@transaction.commit_on_success
def publication_edit(request):
    """Edit/New page of a publication.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    if not request.user.is_authenticated():
        if request.method == 'POST':
            next = '?next=' + request.POST['next']
        else:
            next = ''
        return HttpResponseRedirect(reverse('user_signin') + next)

    if request.method == 'POST':
        # work around a peculiarity within django
        pub = None
        id = int(request.POST['id'])
        if id > 0:
            try:
                pub = Publication.objects.get(pk=id)
                form = PublicationForm(request.POST, instance=pub)
            except Publication.DoesNotExist:
                form = PublicationForm(request.POST)
        else:
            form = PublicationForm(request.POST)

        if form.is_valid():
            if not pub:
                pub = Publication()
            pub.content = form.cleaned_data['content']
            pub.title = form.cleaned_data['title']
            pub.save()
            return HttpResponseRedirect(form.cleaned_data['next'])
        else:
            return HttpResponseRedirect(form.cleaned_data['next'])
    return HttpResponseRedirect(reverse('repository_index'))


#############################################################################
### JSON responses
#############################################################################

def publication_get(request, id):
    """AJAX: Get publication specified by id.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: integer
    @return: publication content in response page
    @rtype: Django response
    """
    try:
        data = serializers.serialize('json',
            [Publication.objects.get(pk=id)], fields=('title', 'content'))
    except Publication.DoesNotExist:
        data = '[{"pk": 0, "model": "repository.publication", "fields": {"content": "", "title": ""}}]'

    return HttpResponse(data, mimetype='text/plain')


def upload_progress(request):
    """Return JSON object with information about the progress of an upload.

    @param request: request data
    @type request: Django request
    @return: progress information
    @rtype: Django response
    """
    progress_id = ''
    if 'X-Progress-ID' in request.GET:
        progress_id = request.GET['X-Progress-ID']
    elif 'X-Progress-ID' in request.META:
        progress_id = request.META['X-Progress-ID']
    if progress_id:
        cache_key = "%s_%s" % (request.META['REMOTE_ADDR'], progress_id)
        data = cache.get(cache_key)
        return HttpResponse(simplejson.dumps(data))
    else:
        return HttpResponseServerError('Server Error: You must provide X-Progress-ID header or query param.')

