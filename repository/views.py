"""
Define the views of app Repository

@var NUM_HISTORY_PAGE: how many versions of an item will be shown on history page
@type NUM_HISTORY_PAGE: integer
@var NUM_INDEX_PAGE: how many items will be shown on index/my page
@type NUM_INDEX_PAGE: integer
"""

import datetime, os, sys, random, subprocess, uuid, traceback
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
from tagging.models import Tag, TaggedItem
from tagging.utils import calculate_cloud
from utils import h5conv
from utils.uploadprogresscachedhandler import UploadProgressCachedHandler


NUM_HISTORY_PAGE = 20
NUM_PAGINATOR_RANGE = 10
PER_PAGE_INTS = [10, 20, 50, 100, 999999]

MEGABYTE = 1048576
UPLOAD_LIMIT = 64 * MEGABYTE

def _get_object_or_404(klass, slug_or_id, version=None):
    """Wrapper for Django's get_object_or_404.

    Retrieves an item by slug or id and checks for ownership.

    @param slug_or_id: item's slug or id for lookup
    @type slug_or_id: string or integer
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: retrieved item
    @rtype: klass
    @raise Http404: if item could not be found
    """
    if version:
        obj = klass.objects.filter(
            slug__text=slug_or_id, is_deleted=False, version=version)
    else:
        obj = klass.objects.filter(
            slug__text=slug_or_id, is_deleted=False, is_current=True)

    if obj: # by slug
        obj = obj[0]
    else: # by id
        try:
            obj = klass.objects.get(pk=slug_or_id)
        except klass.DoesNotExist:
            raise Http404
        if not obj or obj.is_deleted:
            raise Http404

    return obj


def _get_versions_paginator(request, obj):
    """Get a paginator for item versions.

    @param request: request data
    @type request: Django request
    @param obj: item to get versions for
    @type obj: either class Data, Task or Solution
    @return: paginator for item versions
    @rtype: Django paginator
    """
    qs = Q(slug__text=obj.slug.text) & Q(is_deleted=False)
    items = obj.__class__.objects.filter(qs).order_by('version')
    items = [i for i in items if i.can_view(request.user)]
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


def _get_completeness(obj):
    """Determine item's completeness.

    @param obj: item to determine its completeness from
    @type obj: either Data, Task or Solution
    @return: completeness of item as a percentage
    @rtype: integer
    @raise Http404: if given item is not of expected class
    """
    if obj.__class__ == Data:
        attrs = ['tags', 'description', 'license', 'summary', 'urls',
            'publications', 'source', 'measurement_details', 'usage_scenario']
    elif obj.__class__ == Task:
        attrs = ['tags', 'description', 'summary', 'urls', 'publications',
            'input', 'output', 'performance_measure', 'type', 'file']
    elif obj.__class__ == Solution:
        attrs = ['tags', 'description', 'summary', 'urls', 'publications',
            'feature_processing', 'parameters', 'os', 'code',
            'software_packages', 'score']
    else:
        raise Http404

    attrs_len = len(attrs)
    attrs_complete = 0
    for attr in attrs:
        if eval('obj.' + attr):
            attrs_complete += 1
    return int((attrs_complete * 100) / attrs_len)


def _get_rating_form(request, obj):
    """Get a rating form for given item.

    @param request: request data
    @type request: Django request
    @param obj: item to get rating form for
    @type obj: either of Data, Task, Solution
    @return: a rating form
    @rtype: forms.RatingForm
    """
    if not request.user.is_authenticated():
        return None

    current = obj.__class__.objects.get(slug=obj.slug, is_current=True)
    if not current:
        return None

    klassname = current.__class__.__name__
    rklass = eval(klassname + 'Rating')
    try:
        r = rklass.objects.get(user=request.user, repository=current)
        rating_form = RatingForm({'interest': r.interest, 'doc': r.doc})
    except rklass.DoesNotExist:
        rating_form = RatingForm()
    rating_form.action = reverse(
        eval(klassname.lower() + '_rate'), args=[current.id])

    return rating_form


def _get_current_tagged_items(request, klass, tagged):
    """Get current items with specific tag.

    @param klass: klass to find current items for
    @type klass: one of Data, Task, Solution
    @param tagged: tagged items
    @type tagged: list of TaggedItem
    @return: current tagged items
    @rtype: list of Data, Task, Solution
    """
    # without if-construct sqlite3 barfs on AnonymousUser
    if request.user.id:
        qs = (Q(user=request.user) | Q(is_public=True)) & Q(is_current=True)
    else:
        qs = Q(is_public=True) & Q(is_current=True)
    if klass == Data:
        qs &= Q(is_approved=True)

    current = klass.objects.filter(qs).order_by('name')
    l = []
    for c in current:
        for t in tagged:
            if t.object_id == c.id:
                l.append(c)
                break
    return l



def _get_current_tags(request, klass=None):
    """Get current tags available to user.

    @param request: request data
    @type request: Django request
    @param klass: class to retrieve tags for
    @type klass: repository.Data/Task/Solution
    @return: current tags available to user
    @rtype: list of tagging.Tag
    """
    # without if-construct sqlite3 barfs on AnonymousUser
    if request.user.id:
        qs = (Q(user=request.user) | Q(is_public=True)) & Q(is_current=True)
    else:
        qs = Q(is_public=True) & Q(is_current=True)

    if klass:
        if klass == Data:
            qs = qs & Q(is_approved=True)
        tags = Tag.objects.usage_for_queryset(klass.objects.filter(qs), counts=True)
    else:
        tags = Tag.objects.usage_for_queryset(
            Data.objects.filter(qs & Q(is_approved=True)), counts=True)
        tags.extend(Tag.objects.usage_for_queryset(
            Task.objects.filter(qs), counts=True))
        tags.extend(Tag.objects.usage_for_queryset(
            Solution.objects.filter(qs), counts=True))

    current = {}
    for t in tags:
        if not t.name in current:
            current[t.name] = t
        else:
            current[t.name].count += t.count

    return current.values()


def _get_tag_cloud(request):
    """Retrieve tag clouds for all item types.

    @param request: request data
    @type request: Django request
    @return: list of tags with attributes font_size
    @rtype: hash with keys 'data', 'task', 'solution' containing lists of tagging.Tag
    """
    clouds = {
        'Data': None,
        'Task': None,
        'Solution': None,
    }

    for k in clouds.iterkeys():
        c = _get_current_tags(request, klass=eval(k))
        if c:
            clouds[k] = calculate_cloud(c, steps=2)
            random.shuffle(clouds[k])
        else:
            clouds[k] = None

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
    """
    if not request.user.is_authenticated():
        func = eval(klass.__name__.lower() + '_activate')
        url = reverse(func, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = _get_object_or_404(klass, id)
    if obj.can_activate(request.user):
        obj.is_public = True
        obj.set_current()

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
    """
    if not request.user.is_authenticated():
        func = eval(klass.__name__.lower() + '_delete')
        url = reverse(func, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = _get_object_or_404(klass, id)
    if not obj.can_delete(request.user):
        return HttpResponseForbidden()
    obj.is_deleted = True
    obj.save()

    # set new current
    obj = klass.objects.filter(slug=obj.slug).\
        filter(is_deleted=False).order_by('-version')
    if obj:
        obj[0].set_current()
        return HttpResponseRedirect(obj[0].get_absolute_slugurl())

    func = eval(klass.__name__.lower() + '_my')
    return HttpResponseRedirect(reverse(func))


def _download_hit(obj):
    """Increase hit counter for given object.

    @param obj: object to increase counter for
    @type obj: Repository
    """
    current = obj.__class__.objects.get(slug=obj.slug, is_current=True)
    current.downloads += 1
    current.save()



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

    @param first: filename of first file
    @type first: string
    @param second: filename of second file
    @type second: string
    """
    stats_first = os.stat(first)
    stats_second = os.stat(second)
    # index 8 is last modified
    if stats_second[8] > stats_first[8]:
        return True
    else:
        return False


def _download(request, klass, id, type='plain'):
    """Download file relating to item given by id and klass and possibly type.

    @param request: request data
    @type request: Django request
    @param klass: item's class
    @type klass: either Data, Task or Solution
    @param id: id of the relating item
    @type id: integer
    @return: download file response
    @rtype: Django response
    @raise Http404: if given klass is unexpected or file doesn't exist or a conversion error occurred
    """
    obj = _get_object_or_404(klass, id)
    if not obj.can_download(request.user):
        return HttpResponseForbidden()

    fname_export = None
    if type == 'plain':
        if klass == Data or klass == Task:
            fileobj = obj.file
        elif klass == Solution:
            fileobj = obj.score
        else:
            raise Http404
        ctype = 'application/octet-stream'

    elif type == 'xml':
        if not obj.file: # maybe no file attached to this item
            raise Http404
        fname_h5 = os.path.join(MEDIA_ROOT, obj.file.name)
        fname_export = fname_h5 + '.xml'
        if not os.path.exists(fname_export) or _is_newer(fname_export, fname_h5):
            cmd = 'h5dump --xml ' + fname_h5 + ' > ' + fname_export
            if not subprocess.call(cmd, shell=True) == 0:
                mail_admins('Failed conversion of %s to XML' % (fname_h5), cmd)
                raise Http404
        fileobj = File(open(fname_export, 'r'))
        ctype = 'application/xml'

    elif type in ('csv', 'arff', 'libsvm', 'matlab', 'octave'):
        if not obj.file: # maybe no file attached to this item
            raise Http404
        fname_h5 = os.path.join(MEDIA_ROOT, obj.file.name)
        fname_export = fname_h5 + '.' + type
        if not os.path.exists(fname_export) or _is_newer(fname_export, fname_h5):
            h = h5conv.HDF5()
            try:
                h.convert(fname_h5, 'h5', fname_export, type)
            except h5conv.ConversionError, e:
                subject = 'Failed conversion of %s to %s' % (fname_h5, type)
                body = traceback.format_exc() + "\n" + str(e)
                mail_admins(subject, body)
                raise Http404
        fileobj = File(open(fname_export, 'r'))
        if type == 'matlab':
            ctype = 'application/x-matlab'
        else:
            ctype = 'application/' + type

    if not fileobj: # something went wrong
        raise Http404

    response = _sendfile(fileobj, ctype)

    fileobj.close()
    if fname_export: # remove exported file
        os.remove(fname_export)
    _download_hit(obj)
    return response


def data_download_xml(request, id):
    """Download XML file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param id: id of the relating item
    @type id: integer
    @return: download XML file response
    @rtype: Django response
    """
    return _download(request, Data, id, 'xml')


def data_download_csv(request, id):
    """Download CSV file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param id: id of the relating item
    @type id: integer
    @return: download CSV file response
    @rtype: Django response
    """
    return _download(request, Data, id, 'csv')


def data_download_arff(request, id):
    """Download ARFF file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param id: id of the relating item
    @type id: integer
    @return: download ARFF file response
    @rtype: Django response
    """
    return _download(request, Data, id, 'arff')


def data_download_libsvm(request, id):
    """Download LibSVM file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param id: id of the relating item
    @type id: integer
    @return: download LibSVM file response
    @rtype: Django response
    """
    return _download(request, Data, id, 'libsvm')


def data_download_matlab(request, id):
    """Download Matlab file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param id: id of the relating item
    @type id: integer
    @return: download Matlab file response
    @rtype: Django response
    """
    return _download(request, Data, id, 'matlab')


def data_download_octave(request, id):
    """Download Octave file relating to item given by id.

    @param request: request data
    @type request: Django request
    @param id: id of the relating item
    @type id: integer
    @return: download Octave file response
    @rtype: Django response
    """
    return _download(request, Data, id, 'octave')


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
    """
    obj = _get_object_or_404(klass, slug_or_id, version)
    if not obj.can_view(request.user):
        return HttpResponseForbidden()
    if klass == Data and not obj.is_approved:
        return HttpResponseRedirect(reverse(data_new_review, args=[obj.slug]))

    current = obj.__class__.objects.get(slug=obj.slug, is_current=True)
    current.hits += 1
    current.save()

    obj.completeness = _get_completeness(obj)
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
        h5 = h5conv.HDF5()
        if h5.get_fileformat(obj.file.name) == 'h5':
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
        'rating_form': _get_rating_form(request, obj),
        'tagcloud': _get_tag_cloud(request),
        'related': obj.filter_related(request.user),
        'section': 'repository',
    }

    if hasattr(obj, 'data_heldback') and obj.data_heldback:
        info_dict['can_view_heldback'] = obj.data_heldback.can_view(request.user)

    if klass == Data:
        fname_h5 = os.path.join(MEDIA_ROOT, obj.file.name)
        try:
            h5 = h5conv.HDF5()
            info_dict['extract'] = h5.get_extract(fname_h5)
        except Exception, e: # catch exceptions in general, but notify admins
            subject = 'Failed data extract of %s' % (fname_h5)
            body = "Hi Admin!" + "\n\n" + subject + ":\n\n" + str(e)
            mail_admins(subject, body)
            info_dict['extract'] = None

    return render_to_response('repository/item_view.html', info_dict)



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
    if request.method == 'POST':
        request.upload_handlers.insert(0,
            UploadProgressCachedHandler(request=request))
        form = formfunc(request.POST, request.FILES, request=request)

        # manual validation coz it's required for new, but not edited Data
        if not request.FILES and klass == Data:
            form.errors['file'] = ErrorDict({'': _('This field is required.')}).as_ul()

        # check whether file is too large
        if klass == Data:
             if len(request.FILES['file']) > UPLOAD_LIMIT:
                 form.errors['file'] = ErrorDict({'': _('Files is too large! Must be smaller than %dMB!' % (UPLOAD_LIMIT / MEGABYTE))}).as_ul()

        if False or form.is_valid():
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
                    
                    h5 = h5conv.HDF5()
                    new.format = h5.get_fileformat(request.FILES['file'].name)
                    new.file.name = new.get_filename()
                    new.num_instances = -1
                    new.num_attributes = -1
                    new.save()
                elif klass == Task:
                    if 'file' in request.FILES:
                        new.file = request.FILES['file']
                        new.file.name = new.get_filename()
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    new.save()
                elif klass == Solution:
                    if 'score' in request.FILES:
                        new.score = request.FILES['score']
                        new.score.name = new.get_scorename()
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    new.save()
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
        'tagcloud': _get_tag_cloud(request),
        'section': 'repository',
        'upload_limit': "%dMB" % (UPLOAD_LIMIT / MEGABYTE)
    }

    return render_to_response('repository/item_new.html', info_dict)


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
    @raise Http404: if given klass is unexpected
    """
    prev = _get_object_or_404(klass, id)
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
                next.save()
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
            next.set_current()
            return HttpResponseRedirect(next.get_absolute_slugurl())
    else:
        form = formfunc(instance=prev, request=request)

    info_dict = {
        'form': form,
        'object': prev,
        'request': request,
        'publication_form': PublicationForm(),
        'tagcloud': _get_tag_cloud(request),
        'section': 'repository',
    }

    return render_to_response('repository/item_edit.html', info_dict)



def _get_my(user, objects):
    """Get My objects subset out of given objects.

    @param user: user data
    @type user: auth.models.User
    @param objects: queryset to find my subset from
    @type objects: Django queryset
    @return: my objects
    @rtype: list of repository.Data/Task/Solution
    """
    filtered = objects.filter(user=user).order_by('slug')
    return filtered
    # this all would not be necessary if a fixed version (e.g. 0 would always
    # be most current)

    #prev = None
    #idx = -1
    #my = []
    #for o in filtered:
    #    if o.slug == prev and o.is_current:
    #        my[idx] = o
    #    if o.slug != prev:
    #        prev = o.slug
    #        idx += 1
    #        my.append(o)
    #return my


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
        paginator = Paginator(objects, len(objects))
    else:
        paginator = Paginator(objects, int(perpage))

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

def _index(request, klass, my=False, q=None):
    """Index/My page for section given by klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param my: if the page should be a My page or the archive index of the section
    @return: section's index or My page
    @rtype: Django response
    """
    if q:
        # only match name and summary for now
        #Q(version__icontains=q) | Q(description__icontains=q)

        objects = klass.objects.filter(
                Q(name__icontains=q) |
                Q(summary__icontains=q))


        objects = objects.filter(is_deleted=False).order_by('-pub_date')
    else:
        objects = klass.objects.filter(is_deleted=False).order_by('-pub_date')
    if klass == Data:
        objects = objects.filter(is_approved=True)
    if my and request.user.is_authenticated():
        objects = _get_my(request.user, objects)
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

    PER_PAGE=_get_per_page(objects.count())
    info_dict = {
        'request': request,
        'page': _get_page(request, objects, PER_PAGE),
        'klass': klass.__name__,
        'unapproved': unapproved,
        'my_or_archive': my_or_archive,
        'per_page': PER_PAGE,
        'tagcloud': _get_tag_cloud(request),
        'section': 'repository',
    }
    if q:
        info_dict['search_term']=q

    return render_to_response('repository/item_index.html', info_dict)



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
        'tagcloud': _get_tag_cloud(request),
    }
    return render_to_response('repository/index.html', info_dict)

def search_data(request):
    searchform = SearchForm()
    
    if request.method == 'GET':
        try:
            q = request.GET['searchterm'];
            return data_search(request, q)
        except:
            return HttpResponseRedirect('/repository/data')
    else:
        return HttpResponseRedirect('/repository/data')

def data_search(request, q):
    """Index page of Data section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return _index(request, Data, False, q)

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

def data_download(request, id):
    """Download of Data section.

    @param request: request data
    @type request: Django request
    @param id: id of item to download
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _download(request, Data, id)


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

def task_download(request, id):
    """Download of Task section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to download
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _download(request, Task, id)


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

def score_download(request, id):
    """Download of Solution section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to download
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _download(request, Solution, id)



@transaction.commit_on_success
def _data_approve(obj, fname_orig, format):
    """Approve Data item.

    @param obj: object to approve
    @type obj: repository.Data
    @param fname_orig: original filename
    @type fname_orig: string
    @param format: data format of file, given by user
    @type format: string
    @return: the modified, approved object
    @rtype: repository.Data
    """
    h5 = h5conv.HDF5()
    fname_h5 = h5.get_filename(fname_orig)

    if format != 'h5':
        verify = True
        if format == 'uci':
            verify = False
        h5.convert(fname_orig, format, fname_h5, 'h5', obj.seperator, verify=verify)

    if os.path.isfile(fname_h5):
        (obj.num_instances, obj.num_attributes) = h5.get_num_instattr(fname_h5)
        # keep original file for the time being
        #os.remove(fname_orig)
        # for some reason, FileField saves file.name as DATAPATH/<basename>
        obj.file.name = os.path.sep.join([DATAPATH, fname_h5.split(os.path.sep)[-1]])

    obj.format = format
    obj.is_approved = True
    obj.save()
    return obj


@transaction.commit_on_success
def _data_conversion_error(request, obj, error):
    """Handle conversion error for Data file.

    @param request: request data
    @type request: Django request
    @param obj: Data item
    @type obj: repository.Data
    @param error: the error that occurred
    @type error: h5conv.ConversionError
    """
    if obj.tags:
        obj.tags += ', conversion_failed'
    else:
        obj.tags = 'conversion_failed'

    obj.is_approved = True
    obj.save()

    url = 'http://' + request.META['HTTP_HOST'] + reverse(
        data_view_slug, args=[obj.slug])
    subject = 'Failed conversion to HDF5: %s' % url
    body = "Hi admin!\n\n" +\
        'URL: ' + url + "\n\n" +\
        traceback.format_exc() + "\n" + str(error)
    mail_admins(subject, body)


@transaction.commit_on_success
def data_new_review(request, slug):
    """Review Data item to check if uploaded file is as expected.

    @param request: request data
    @type request: Django request
    @param slug: slug of the item to review
    @type slug: string
    @return: redirect user to login page or item's view page after approval or review form
    @rtype: Django response
    """
    if not request.user.is_authenticated():
        next = '?next=' + reverse(data_new_review, args=[slug])
        return HttpResponseRedirect(reverse('user_signin') + next)

    obj = _get_object_or_404(Data, slug)
    # don't want users to be able to remove items once approved
    if not obj.can_edit(request.user) or obj.is_approved:
        return HttpResponseForbidden()

    fname = os.path.join(MEDIA_ROOT, obj.file.name)
    if request.method == 'POST':
        if request.POST.has_key('revert'):
            os.remove(fname)
            obj.delete()
            return HttpResponseRedirect(reverse(data_new))
        elif request.POST.has_key('approve'):
            obj.seperator = request.POST['id_seperator']
            try:
                obj = _data_approve(obj, fname, request.POST['id_format'].lower())
            except h5conv.ConversionError, e:
                _data_conversion_error(request, obj, e)
            return HttpResponseRedirect(
                reverse(data_view_slug, args=[obj.slug]))

    h5 = h5conv.HDF5()
    if obj.format == 'h5':
        obj.seperator = ''
    else:
        obj.seperator = h5.infer_seperator(fname)

    info_dict = {
        'object': obj,
        'request': request,
        'tagcloud': _get_tag_cloud(request),
        'section': 'repository',
        'extract': h5.get_extract(fname),
    }
    return render_to_response('repository/data_new_review.html', info_dict)



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
        tagged = TaggedItem.objects.filter(tag=tag)
        objects = _get_current_tagged_items(request, klass, tagged)
        if not objects:
            raise Http404
    except Tag.DoesNotExist:
        raise Http404

    info_dict = {
        'request': request,
        'section': 'repository',
        'klass': klass.__name__,
        'tag': tag,
        'tagcloud': _get_tag_cloud(request),
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
    """
    if not request.user.is_authenticated():
        next = '?next=' + reverse(eval(klass.__name__.lower() + '_rate'), args=[id])
        return HttpResponseRedirect(reverse('user_signin') + next)

    rklass = eval(klass.__name__ + 'Rating')
    obj = get_object_or_404(klass, pk=id)
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
            #print request.POST
            #print form.errors
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

