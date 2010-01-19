"""
Define the views of app Repository

@var NUM_HISTORY_PAGE: how many versions of an item will be shown on history page
@type NUM_HISTORY_PAGE: integer
@var NUM_INDEX_PAGE: how many items will be shown on index/my page
@type NUM_INDEX_PAGE: integer
"""

import datetime, os, random
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden, Http404
from django.db import IntegrityError, transaction
from django.utils.translation import ugettext as _
from django.forms.util import ErrorDict
from django.db.models import Q
from tagging.models import Tag, TaggedItem
from tagging.utils import calculate_cloud
from repository.models import *
from repository.forms import *
from settings import MEDIA_ROOT, TAG_SPLITSTR
from utils import hdf5conv


NUM_HISTORY_PAGE = 20
NUM_INDEX_PAGE = 10



def _get_object_or_404(request, slug_or_id, klass):
    """Wrapper for Django's get_object_or_404.

    Retrieves an item by slug or id and checks for ownership.

    @param request: request data
    @type request: Django request
    @param slug_or_id: item's slug or id for lookup
    @type slug_or_id: string or integer
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: retrieved item
    @rtype: klass
    @raise Http404: item could not be found
    """
    obj = CurrentVersion.objects.filter(slug__text=slug_or_id,
        repository__is_deleted=False)
    if obj: # slug + current version
        obj = getattr(obj[0].repository, klass.__name__.lower())
    else: # id
        try:
            obj = klass.objects.get(pk=slug_or_id)
        except klass.DoesNotExist:
            raise Http404
        if not obj or obj.is_deleted:
            raise Http404

    obj.slug_or_id = slug_or_id
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
    items = [i for i in items if i.is_readable(request.user)]
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
        attrs = ['tags', 'description', 'license', 'summary', 'urls', 'publications', 'source', 'measurement_details', 'usage_scenario']
    elif obj.__class__ == Task:
        attrs = ['tags', 'description', 'summary', 'urls', 'publications', 'input', 'output', 'performance_measure', 'type', 'splits']
    elif obj.__class__ == Solution:
        attrs = ['tags', 'description', 'summary', 'urls', 'publications', 'feature_processing', 'parameters', 'os', 'code', 'score']
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
    rating_form = None
    if request.user.is_authenticated() and not request.user == obj.user:
        klassname = obj.__class__.__name__
        rklass = eval(klassname + 'Rating')
        try:
            r = rklass.objects.get(user__id=request.user.id, repository=obj)
            rating_form = RatingForm({
                'interesting': r.interesting,
                'documentation': r.documentation,
            })
        except rklass.DoesNotExist:
            rating_form = RatingForm()
        rating_form.action = reverse(
            eval(klassname.lower() + '_rate'), args=[obj.id])

    return rating_form


def _get_latest(request):
    """Get latest items of each type.

    @param request: request data
    @type request: Django request
    @return: latest items of each type
    @rtype: dict
    """
    qs = Q(is_deleted=False) & (Q(is_public=True) | Q(user=request.user))
    latest = {}
    try:
        latest['data'] = Data.objects.filter(qs).order_by('-pub_date')[0]
    except IndexError:
        latest['data'] = None
    try:
        latest['task'] = Task.objects.filter(qs).order_by('-pub_date')[0]
    except IndexError:
        latest['task'] = None
    try:
        latest['solution'] = Solution.objects.filter(qs).order_by('-pub_date')[0]
    except IndexError:
        latest['solution'] = None

    return latest



def _get_current_tags(request):
    """Get current tags available to user.

    @param request: request data
    @type request: Django request
    @return: current tags available to user
    @rtype: list of tagging.Tag
    """
    current = CurrentVersion.objects.filter(
            Q(repository__user=request.user.id) | Q(repository__is_public=True)
    )
    if current:
        all = Tag.objects.all()
        tags = []
        for tag in all:
            found = False
            tag.count = 0
            for item in tag.items.values():
                for object in current:
                    if item['object_id'] == object.repository.id:
                        found = True
                        tag.count += 1
            if found:
                tags.append(tag)
    else:
        tags = None

    return tags



def _get_tag_cloud(request):
    """Retrieve a cloud of tags of all item types.

    @param request: request data
    @type request: Django request
    @return: list of tags with attributes font_size
    @rtype: list of tagging.Tag
    """
    current = _get_current_tags(request)
    if current:
        cloud = calculate_cloud(current, steps=2)
        random.shuffle(cloud)
    else:
        cloud = None
    return cloud



def _can_activate(request, obj):
    """Determine if given item can be activated by the user.

    @param request: request data
    @type request: Django request
    @param obj: item to be activated
    @type obj: either Data, Task or Solution
    @return: if user can activate given item
    @rtype: boolean
    """
    if not obj.is_writeable(request.user):
        return False
    if not obj.is_public:
        return True

    # if obj is public, but not current version:
    try:
        cv = CurrentVersion.objects.get(slug=obj.slug)
        if not cv.repository_id == obj.id:
            return True
    except CurrentVersion.DoesNotExist:
        pass

    return False


@transaction.commit_on_success
def _activate(request, id, klass):
    """Activate item given by id and klass.

    @param request: request data
    @type request: Django request
    @param id: id of the item to activate
    @type id: integer
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: redirect user to login page or item's page
    @rtype: Django response
    """
    if not request.user.is_authenticated():
        func = eval(klass.__name__.lower() + '_activate')
        url = reverse(func, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = _get_object_or_404(request, id, klass)
    if not obj.is_writeable(request.user):
        return HttpResponseForbidden()
    obj.is_public = True
    obj.save()
    CurrentVersion.set(obj)

    return HttpResponseRedirect(obj.get_absolute_slugurl())


@transaction.commit_on_success
def _delete(request, id, klass):
    """Delete item given by id and klass.

    @param request: request data
    @type request: Django request
    @param id: id of the item to delete
    @type id: integer
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: redirect user to login page or item's page or user's my page
    @rtype: Django response
    """
    if not request.user.is_authenticated():
        func = eval(klass.__name__.lower() + '_delete')
        url = reverse(func, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = _get_object_or_404(request, id, klass)
    if not obj.is_writeable(request.user):
        return HttpResponseForbidden()
    obj.is_deleted = True
    obj.save()

    current = klass.objects.filter(slug=obj.slug).\
        filter(is_deleted=False).order_by('-version')
    if current:
        CurrentVersion.set(current[0])
        return HttpResponseRedirect(current[0].get_absolute_slugurl())

    func = eval(klass.__name__.lower() + '_my')
    return HttpResponseRedirect(reverse(func))


def _download(request, id, klass):
    """Download file relating to item given by id and klass.

    @param request: request data
    @type request: Django request
    @param id: id of the relating item
    @type id: integer
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: contents of file related to object
    @rtype: binary file
    @raise Http404: if given klass is unexpected
    """
    obj = _get_object_or_404(request, id, klass)
    if not obj.is_readable(request.user):
        return HttpResponseForbidden()

    if klass == Data:
        fileobj = obj.file
    elif klass == Task:
        fileobj = obj.splits
    elif klass == Solution:
        fileobj = obj.score
    else:
        raise Http404

    # fails to work when OpenID Middleware is activated
#    filename = os.path.join(MEDIA_ROOT, fileobj.name)
#    wrapper = FileWrapper(file(filename))
#    response = HttpResponse(wrapper, content_type='application/octet-stream')
    # not sure if this alternative is a memory hog...
    response = HttpResponse()
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Length'] = fileobj.size
    response['Content-Disposition'] = 'attachment; filename=' + fileobj.name
    for chunk in fileobj.chunks():
        response.write(chunk)

    obj.downloads += 1
    obj.save()

    return response



def _view(request, slug_or_id, klass):
    """View item given by slug or id and klass.

    @param request: request data
    @type request: Django request
    @param slug_or_id: slug or id of the item to activate
    @type slug_or_id: string or integer
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: view page or review page if klass Data and item not approved
    @rtype: Django response
    """
    obj = _get_object_or_404(request, slug_or_id, klass)
    if not obj.is_readable(request.user):
        return HttpResponseForbidden()
    if klass == Data and not obj.is_approved:
        return HttpResponseRedirect(reverse(data_new_review, args=[slug_or_id]))

    obj.hits += 1
    obj.save()

    obj.completeness = _get_completeness(obj)
    obj.klass = klass.__name__
    # need tags in list
    obj.tags = obj.tags.split(TAG_SPLITSTR)
    obj.versions = _get_versions_paginator(request, obj)
    klassname = klass.__name__.lower()
    obj.url_activate = reverse(eval(klassname + '_activate'), args=[obj.id])
    obj.url_edit = reverse(eval(klassname + '_edit'), args=[obj.id])
    obj.url_delete = reverse(eval(klassname + '_delete'), args=[obj.id])

    info_dict = {
        'object': obj,
        'request': request,
        'can_activate': _can_activate(request, obj),
        'can_delete': obj.is_writeable(request.user),
        'rating_form': _get_rating_form(request, obj),
        'tagcloud': _get_tag_cloud(request),
        'section': 'repository',
    }
    if klass == Data:
        info_dict['extract'] = hdf5conv.get_extract(
            os.path.join(MEDIA_ROOT, obj.file.name))

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
        form = formfunc(request.POST, request.FILES, request=request)

        # manual validation coz it's required for new, but not edited Data
        if not request.FILES and klass == Data:
            form.errors['file'] = ErrorDict({'': _('This field is required.')}).as_ul()

        if form.is_valid():
            new = form.save(commit=False)
            new.pub_date = datetime.datetime.now()
            try:
                new.slug_id = new.get_slug_id()
            except IntegrityError:
                # looks quirky...
                d = ErrorDict({'':
                    _('The given name yields an already existing slug. Please try another name.')})
                form.errors['name'] = d.as_ul()
            else:
                new.version = 1
                # set to invisible for public until activated / made public
                new.is_public = False
                new.user = request.user

                if not form.cleaned_data['keep_private']:
                    new.is_public = True

                if klass == Data:
                    new.file = request.FILES['file']
                    new.format = hdf5conv.get_fileformat(request.FILES['file'].name)
                    new.file.name = new.get_filename()
                    new.save()
                    func = eval(klass.__name__.lower() + '_new_review')
                elif klass == Task:
                    if 'splits' in request.FILES:
                        new.splits = request.FILES['splits']
                        new.splits.name = new.get_splitname()
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    new.save()
                    form.save_m2m() # a bit odd
                    CurrentVersion.set(new)
                    func = eval(klass.__name__.lower() + '_view')
                elif klass == Solution:
                    if 'score' in request.FILES:
                        new.score = request.FILES['score']
                        new.score.name = new.get_scorename()
                    new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                    new.save()
                    new.save()
                    CurrentVersion.set(new)
                    func = eval(klass.__name__.lower() + '_view')
                else:
                    raise Http404
                return HttpResponseRedirect(reverse(func, args=[new.id]))
    else:
        form = formfunc(request=request)

    info_dict = {
        'klass': klass.__name__,
        'url_new': url_new,
        'form': form,
        'request': request,
        'tagcloud': _get_tag_cloud(request),
        'section': 'repository',
    }

    return render_to_response('repository/item_new.html', info_dict)



@transaction.commit_on_success
def _edit(request, slug_or_id, klass):
    """Edit existing item given by slug or id and klass.

    @param request: request data
    @type request: Django request
    @param slug_or_id: slug or id of the item to activate
    @type slug_or_id: string or integer
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: user login page, item's view page or this page again on failed form validation
    @rtype: Django response
    @raise Http404: if given klass is unexpected
    """
    prev = _get_object_or_404(request, slug_or_id, klass)
    prev.klass = klass.__name__
    prev.url_edit = reverse(
        eval(klass.__name__.lower() + '_edit'), args=[prev.id])
    if not request.user.is_authenticated():
        return HttpResponseRedirect(
            reverse('user_signin') + '?next=' + prev.url_edit)
    if not prev.is_writeable(request.user):
        return HttpResponseForbidden()

    formfunc = eval(klass.__name__ + 'Form')
    if request.method == 'POST':
        request.POST['name'] = prev.name # cheat a little
        form = formfunc(request.POST, request=request)

        if form.is_valid():
            next = form.save(commit=False)
            next.pub_date = datetime.datetime.now()
            next.slug_id = prev.slug_id
            next.version = next.get_next_version()
            next.user_id = request.user.id

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
                if 'splits' in request.FILES:
                    next.splits = request.FILES['splits']
                    next.splits.name = next.get_splitname()
                    filename = os.path.join(MEDIA_ROOT, prev.splits.name)
                    if os.path.isfile(filename):
                        os.remove(filename)
                else:
                    next.splits = prev.splits

                next.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                next.save()
                form.save_m2m() # a bit odd
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
            CurrentVersion.set(next)
            return HttpResponseRedirect(next.get_absolute_slugurl())
    else:
        form = formfunc(instance=prev, request=request)

    info_dict = {
        'form': form,
        'object': prev,
        'request': request,
        'tagcloud': _get_tag_cloud(request),
        'section': 'repository',
    }

    return render_to_response('repository/item_edit.html', info_dict)



def _index(request, klass, my=False):
    """Index/My page for section given by klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param my: if the page should be a My page or the archive index of the section
    @return: section's index or My page
    @rtype: Django response
    """
    objects = CurrentVersion.objects.filter(
        type=TYPE[klass.__name__],
        repository__is_deleted=False
    ).order_by('-repository__pub_date')

    if my:
        objects = objects.filter(repository__user=request.user)
        if klass == Data:
            unapproved = klass.objects.filter(
                user=request.user,
                is_approved=False
            )
        else:
            unapproved = None
        my_or_archive = _('My')
    else:
        objects = objects.filter(repository__is_public=True)
        unapproved = None
        my_or_archive = _('Public Archive')

    paginator = Paginator(objects, NUM_INDEX_PAGE)
    try:
        num = int(request.GET.get('page', '1'))
    except ValueError:
        num = 1
    try:
        page = paginator.page(num)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)

    # quirky, but simplifies templates
    for obj in page.object_list:
        obj.absolute_url = getattr(obj.repository, klass.__name__.lower()).\
            get_absolute_slugurl()

    info_dict = {
        'request': request,
        'page': page,
        'klass': klass.__name__,
        'unapproved': unapproved,
        'my_or_archive': my_or_archive,
        'tagcloud': _get_tag_cloud(request),
        'section': 'repository',
    }
    return render_to_response('repository/item_index.html', info_dict)



def index(request):
    """Index page of app repository.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    info_dict = {
#        'latest': _get_latest(request),
        'request': request,
        'section': 'repository',
        'tagcloud': _get_tag_cloud(request),
    }
    return render_to_response('repository/index.html', info_dict)



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

def data_view(request, slug_or_id):
    """View page of Data section.

    @param request: request data
    @type request: Django request
    @param slug_or_id: slug or id of item to view
    @type slug_or_id: string or integer
    @return: rendered response page
    @rtype: Django response
    """
    return _view(request, slug_or_id, Data)

def data_edit(request, slug_or_id):
    """Edit page of Data section.

    @param request: request data
    @type request: Django request
    @param slug_or_id: slug or id of item to edit
    @type slug_or_id: string or integer
    @return: rendered response page
    @rtype: Django response
    """
    return _edit(request, slug_or_id, Data)

def data_delete(request, id):
    """Delete of Data section.

    @param request: request data
    @type request: Django request
    @param id: id of item to delete
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _delete(request, id, Data)

def data_activate(request, id):
    """Activate of Data section.

    @param request: request data
    @type request: Django request
    @param id: id of item to activate
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _activate(request, id, Data)

def data_download(request, id):
    """Download of Data section.

    @param request: request data
    @type request: Django request
    @param id: id of item to download
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _download(request, id, Data)


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

def task_view(request, slug_or_id):
    """View page of Task section.

    @param request: request data
    @type request: Django request
    @param slug_or_id: slug or id of the item to view
    @type slug_or_id: string or integer
    @return: rendered response page
    @rtype: Django response
    """
    return _view(request, slug_or_id, Task)

def task_edit(request, slug_or_id):
    """Edit page of Task section.

    @param request: request data
    @type request: Django request
    @param slug_or_id: slug or id of item to edit
    @type slug_or_id: string or integer
    @return: rendered response page
    @rtype: Django response
    """
    return _edit(request, slug_or_id, Task)

def task_delete(request, id):
    """Delete of Task section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to delete
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _delete(request, id, Task)

def task_activate(request, id):
    """Activate of Task section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to activate
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _activate(request, id, Task)

def splits_download(request, id):
    """Download of Task section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to download
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _download(request, id, Task)


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

def solution_view(request, slug_or_id):
    """View page of Solution section.

    @param request: request data
    @type request: Django request
    @param slug_or_id: slug or id of the item to view
    @type slug_or_id: string or integer
    @return: rendered response page
    @rtype: Django response
    """
    return _view(request, slug_or_id, Solution)

def solution_edit(request, slug_or_id):
    """Edit page of Solution section.

    @param request: request data
    @type request: Django request
    @param slug_or_id: slug or id of item to edit
    @type slug_or_id: string or integer
    @return: rendered response page
    @rtype: Django response
    """
    return _edit(request, slug_or_id, Solution)

def solution_activate(request, id):
    """Activate of Solution section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to activate
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _activate(request, id, Solution)

def solution_delete(request, id):
    """Delete of Solution section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to delete
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _delete(request, id, Solution)

def score_download(request, id):
    """Download of Solution section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to download
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return _download(request, id, Solution)



@transaction.commit_on_success
def data_new_review(request, id):
    """Review Data item to check if uploaded file is as expected.

    @param request: request data
    @type request: Django request
    @param id: id of the item to review
    @type id: integer
    @return: redirect user to login page or item's view page after approval or review form
    @rtype: Django response
    """
    if not request.user.is_authenticated():
        next = '?next=' + reverse(data_new_review, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + next)

    obj = _get_object_or_404(request, id, Data)
    # don't want users to be able to remove items once approved
    if not obj.is_writeable(request.user) or obj.is_approved:
        return HttpResponseForbidden()

    if request.method == 'POST':
        if request.POST.has_key('revert'):
            os.remove(os.path.join(MEDIA_ROOT, obj.file.name))
            obj.delete()
            return HttpResponseRedirect(reverse(data_new))
        elif request.POST.has_key('approve'):
            uploaded = os.path.join(MEDIA_ROOT, obj.file.name)
            converted = hdf5conv.get_filename(uploaded)

            format = request.POST['id_format'].lower()
            if format != 'hdf5':
                try:
                    hdf5conv.convert(uploaded, format, converted, 'hdf5')
                    format = 'hdf5'
                except Exception:
                    pass
            obj.format = format

            if os.path.isfile(converted): # assign converted file to obj
                os.remove(uploaded)
                # for some reason, FileField saves file.name as DATAPATH/<basename>
                obj.file.name = os.path.sep.join([DATAPATH, converted.split(os.path.sep)[-1]])

            obj.is_approved = True
            obj.save()
            CurrentVersion.set(obj)
            return HttpResponseRedirect(reverse(data_view, args=[obj.id]))

    info_dict = {
        'object': obj,
        'request': request,
        'tagcloud': _get_tag_cloud(request),
        'section': 'repository',
        'extract': hdf5conv.get_extract(os.path.join(MEDIA_ROOT, obj.file.name)),
    }
    return render_to_response('repository/data_new_review.html', info_dict)



def tags_index(request):
    """Index page to display all public and all user's tags.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    info_dict = {
        'request': request,
        'section': 'repository',
        'tags': _get_current_tags(request),
    }
    return render_to_response('repository/tags_index.html', info_dict)


def tags_view(request, tag):
    """View all items tagged by given tag.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    @return: rendered response page
    @rtype: Django response
    @raise Http404: if an item's class is unexpected
    """
    try:
        current = CurrentVersion.objects.filter(
                Q(repository__user=request.user.id) | Q(repository__is_public=True)
        )
        tag = Tag.objects.get(name=tag)
        tagged = TaggedItem.objects.filter(tag=tag)
        objects = []
        for c in current:
            for t in tagged:
                if t.object_id == c.repository.id:
                    try:
                        o = c.repository.data
                    except:
                        try:
                            o = c.repository.task
                        except:
                            try:
                                o = c.repository.solution
                            except:
                                raise Http404
                    objects.append(o)
                    break
    except Tag.DoesNotExist:
        objects = None

    info_dict = {
        'request': request,
        'section': 'repository',
        'tag': tag,
        'tagcloud': _get_tag_cloud(request),
        'objects': objects,
    }
    return render_to_response('repository/tags_view.html', info_dict)



def _rate(request, id, klass):
    """Rate an item given by id and klass.

    @param id: item's id
    @type id: integer
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @return: redirect to item's view page
    @rtype: Django response
    """
    rklass = eval(klass.__name__ + 'Rating')
    obj = get_object_or_404(klass, pk=id)
    if request.user.is_authenticated() and not request.user == obj.user:
        if request.method == 'POST':
            form=RatingForm(request.POST)
            if form.is_valid():
                r, fail = rklass.objects.get_or_create(user=request.user, repository=obj)
                r.update_rating(
                    form.cleaned_data['interesting'],
                    form.cleaned_data['documentation'],
                )

    return HttpResponseRedirect(obj.get_absolute_url())


def data_rate(request, id):
    return _rate(request, id, Data)
def task_rate(request, id):
    return _rate(request, id, Task)
def solution_rate(request, id):
    return _rate(request, id, Solution)

