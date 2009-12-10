"""
All custom repository logic is kept here
"""

import datetime, os
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db import IntegrityError
from django.utils.translation import ugettext as _
from django.forms.util import ErrorDict
from django.db.models import Q
from tagging.models import Tag, TaggedItem
from repository.models import *
from repository.forms import *
from settings import MEDIA_ROOT, TAG_SPLITCHAR
from utils import hdf5conv


VERSIONS_PER_PAGE = 5
OBJECTS_PER_PAGE = 10


def _is_owner(request_user, obj_user):
    if request_user.is_staff or\
        request_user.is_superuser or\
        request_user == obj_user:
        return True
    else:
        return False


def _get_object_or_404(request, klass, slug_or_id):
    obj = CurrentVersion.objects.filter(slug__text=slug_or_id,
        repository__is_deleted=False)

    if obj: # slug + current version
        is_owner = _is_owner(request.user, obj[0].repository.user)
        if not is_owner and not obj[0].repository.is_public:
            raise Http404
        obj = getattr(obj[0].repository, klass.__name__.lower())
    else: # id
        try:
            obj = klass.objects.get(pk=slug_or_id)
        except klass.DoesNotExist:
            raise Http404
        if not obj or obj.is_deleted:
            raise Http404
        is_owner = _is_owner(request.user, obj.user)
        if not is_owner and not obj.is_public:
            raise Http404

    obj.slug_or_id = slug_or_id
    return obj


def _get_versions_paginator(request, obj, is_owner):
    versions = Data.objects.values('id', 'version').\
        filter(slug__text=obj.slug.text).\
        filter(is_deleted=False).order_by('version')
    if not is_owner:
        versions = versions.filter(is_public=True)
    paginator = Paginator(versions, VERSIONS_PER_PAGE)

    try:
        # dunno a better way than looping thru, since index != obj.version
        index = 0
        for v in versions:
            if v['id'] == obj.id:
                break
            else:
                index += 1
        default_page = (index / VERSIONS_PER_PAGE) + 1
        page = int(request.GET.get('page', str(default_page)))
    except ValueError:
        page = 1
    try:
        versions = paginator.page(page)
    except (EmptyPage, InvalidPage):
        versions = paginator.page(paginator.num_pages)

    return versions



def index(request):
    try:
        latest_data = Data.objects.filter(is_deleted=False, is_public=True).order_by('-pub_date')[0]
    except IndexError:
        latest_data = None
    try:
        latest_task = Task.objects.latest()
    except Task.DoesNotExist:
        latest_task = None
    try:
        latest_solution = Solution.objects.latest()
    except Solution.DoesNotExist:
        latest_solution = None

    info_dict = {
        'latest_data': latest_data,
        'latest_task': latest_task,
        'latest_solution': latest_solution,
        'request': request,
    }
    return render_to_response('repository/index.html', info_dict)


def rate(request, type, id):
    try:
        trash = TYPE[type]
    except KeyError: # user tries nasty things
        klass = Data
        rklass = DataRating
    else:
        klass = eval(type.capitalize())
        rklass = eval(type.capitalize() + 'Rating')

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



def _repository_index(request, type, my=False):
    objects = CurrentVersion.objects.filter(type=TYPE[type],
        repository__is_deleted=False).order_by('-repository__pub_date')

    if my:
        objects = objects.filter(repository__user=request.user.id)
#        klass = eval(type.capitalize())
#        unapproved = klass.objects.filter(
#            user=request.user.id,
#            is_approved=False
#        )
        my_or_archive = _('My')
    else:
        objects = objects.filter(repository__is_public=True)
        my_or_archive = _('Public Archive')

    paginator = Paginator(objects, OBJECTS_PER_PAGE)
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
        obj.absolute_url = getattr(obj.repository, type).\
            get_absolute_url(use_slug=True)

    info_dict = {
        'request': request,
        'page': page,
        'type': type.capitalize(),
        'my_or_archive': my_or_archive,
    }
    return render_to_response('repository/repository_index.html', info_dict)

def data_index(request):
    return _repository_index(request, 'data')
def data_my(request):
    return _repository_index(request, 'data', True)
def task_index(request):
    return _repository_index(request, 'task')
def solution_index(request):
    return _repository_index(request, 'solution')


def data_new(request):
    if not request.user.is_authenticated():
        next = '?next=' + reverse(data_new)
        return HttpResponseRedirect(reverse('user_signin') + next)

    if request.method == 'POST':
        form = DataForm(request.POST, request.FILES)

        # manual validation coz it's required for new, but not edited data
        is_required = ErrorDict({'': _('This field is required.')}).as_ul()
        if not request.FILES:
            form.errors['file'] = is_required

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
                # set to invisible until approved by review
                new.is_public = False
                new.user_id = request.user.id
                new.file = request.FILES['file']
                new.format = hdf5conv.get_fileformat(request.FILES['file'].name)
                new.file.name = new.get_filename()
                new.save()
                return HttpResponseRedirect(reverse(data_new_review, args=[new.id]))
    else:
        form = DataForm()

    info_dict = {
        'form': form,
        'request': request,
    }
    return render_to_response('repository/data_new.html', info_dict)


def data_new_review(request, id):
    if not request.user.is_authenticated():
        next = '?next=' + reverse(data_new_review, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + next)

    obj = _get_object_or_404(request, Data, id)
    # don't want users to be able to remove items once approved
    if obj.is_approved:
        raise Http404

    if request.method == 'POST':
        if request.POST.has_key('back'):
            os.remove(os.path.join(MEDIA_ROOT, obj.file.name))
            obj.delete()
            return HttpResponseRedirect(reverse(data_new))
        elif request.POST.has_key('ok'):
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
            CurrentVersion.edit(obj)
            return HttpResponseRedirect(reverse(data_view, args=[obj.id]))

    info_dict = {
        'object': obj,
        'request': request,
        'extract': hdf5conv.get_extract(os.path.join(MEDIA_ROOT, obj.file.name)),
    }
    return render_to_response('repository/data_new_review.html', info_dict)


def data_edit(request, slug_or_id):
    prev = _get_object_or_404(request, Data, slug_or_id)
    url = reverse(data_edit, args=[prev.slug_or_id])
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    if request.method == 'POST':
        request.POST['name'] = prev.name # cheat a little
        form = DataForm(request.POST)
        if form.is_valid():
            next = form.save(commit=False)
            next.pub_date = datetime.datetime.now()
            next.slug_id = prev.slug_id
            next.file = prev.file
            next.format = prev.format
            next.version = next.get_next_version()
            next.user_id = request.user.id
            next.is_approved = prev.is_approved
            next.save()
            CurrentVersion.edit(next)
            return HttpResponseRedirect(next.get_absolute_url(True))
    else:
        form = DataForm(instance=prev)

    info_dict = {
        'form': form,
        'prev': prev,
        'request': request,
    }
    return render_to_response('repository/data_edit.html', info_dict)


def _data_completeness(obj):
    attrs = ['tags', 'description', 'license', 'summary', 'urls', 'publications', 'source', 'measurement_details', 'usage_scenario']
    attrs_len = len(attrs)
    attrs_complete = 0
    for attr in attrs:
        if eval('obj.' + attr):
            attrs_complete += 1
    return int((attrs_complete * 100) / attrs_len)


def _data_can_activate(obj, is_owner):
    if not is_owner:
        return False

    if not obj.is_public:
        return True

    try:
        cv = CurrentVersion.objects.get(slug=obj.slug)
        if not cv.repository_id == obj.id:
            return True
    except CurrentVersion.DoesNotExist:
        pass

    return False


def _data_rating_form(request, obj):
    rating_form = None
    if request.user.is_authenticated() and not request.user == obj.user:
        try:
            r = DataRating.objects.get(user__id=request.user.id, repository=obj)
            rating_form= RatingForm({
                'interesting': r.interesting,
                'documentation': r.documentation,
            })
        except DataRating.DoesNotExist:
            rating_form = RatingForm()

    return rating_form

def data_view(request, slug_or_id):
    obj = _get_object_or_404(request, Data, slug_or_id)
    if not obj.is_approved:
        return HttpResponseRedirect(reverse(data_new_review, args=[slug_or_id]))

    obj.completeness = _data_completeness(obj)
    # need tags in list
    obj.tags = obj.tags.split(TAG_SPLITCHAR)
    is_owner = _is_owner(request.user, obj.user)
    obj.versions = _get_versions_paginator(request, obj, is_owner)

    info_dict = {
        'object': obj,
        'request': request,
        'can_activate': _data_can_activate(obj, is_owner),
        'can_delete': is_owner,
        'rating_form': _data_rating_form(request, obj),
        'extract': hdf5conv.get_extract(os.path.join(MEDIA_ROOT, obj.file.name)),
    }

    return render_to_response('repository/data_view.html', info_dict)


def data_delete(request, slug_or_id):
    obj = _get_object_or_404(request, Data, slug_or_id)
    if _is_owner(request.user, obj.user):
        obj.is_deleted = True
        obj.save()
        current = Data.objects.filter(slug=obj.slug).\
            filter(is_deleted=False).order_by('-version')
        if current:
            CurrentVersion.edit(current[0])

    return HttpResponseRedirect(reverse(data_my))


def data_activate(request, id):
    if not request.user.is_authenticated():
        url=reverse(data_activate, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = get_object_or_404(Data, pk=id)
    if not _is_owner(request.user, obj.user):
        raise Http404

    obj.is_public = True
    obj.save()
    CurrentVersion.edit(obj)

    return HttpResponseRedirect(obj.get_absolute_url(use_slug=True))


def data_download(request, id):
    obj = _get_object_or_404(request, Data, id)
    filename = os.path.join(MEDIA_ROOT, obj.file.name)
    wrapper = FileWrapper(file(filename))
    response = HttpResponse(wrapper, mimetype='application/octet-stream')
    response['Content-Length'] = os.path.getsize(filename)
    response['Content-Disposition'] = 'attachment; filename=' + obj.file.name
    return response



def task_new(request):
    return render_to_response('repository/task_new.html')

def task_view(request, slug_or_idid):
    return render_to_response('repository/task_view.html')

def task_edit(request, slug_or_id):
    return render_to_response('repository/task_view.html')


def solution_new(request):
    return render_to_response('repository/solution_new.html')

def solution_view(request, id):
    return render_to_response('repository/solution_view.html')



# seems quirky...
# get Data queryset of current version items
def _tags_queryset(request):
    cvlist = CurrentVersion.objects.filter(
            (Q(repository__user=request.user.id) |\
             Q(repository__is_public=True)) &\
            Q(repository__is_deleted=False) &\
            Q(type=TYPE['data'])).values('repository_id')

    if len(cvlist) == 0:
        return Data.objects.none()

    where = []
    for cv in cvlist:
        where.append(str(cv['repository_id']))
    where = 'id IN (' + ', '.join(where) + ')'

    return Data.objects.extra(where=[where])


def tags_index(request):
    queryset = _tags_queryset(request)
    if queryset:
        # doesn't retrieve data from queryset only, but seemingly from Model
        # tags = Tag.objects.usage_for_queryset(queryset, counts=True)
        all = Tag.objects.usage_for_model(Data)
        tags = []
        for tag in all:
            found = False
            tag.count = 0
            for item in tag.items.values():
                for data in queryset:
                    if item['object_id'] == data.id:
                        found = True
                        tag.count += 1
            if found:
                tags.append(tag)
    else:
        tags = None

    info_dict = {
        'request': request,
        'tags': tags,
    }
    return render_to_response('repository/tags_index.html', info_dict)


def tags_view(request, tag):
    try:
        queryset = _tags_queryset(request)
        tag = Tag.objects.get(name=tag)
        # generates ambigous column name error: id
        #object_list = TaggedItem.objects.get_by_model(queryset, tag)
        # so we do this:
        tagged_list = TaggedItem.objects.get_by_model(Data, tag)
        object_list = []
        for data in queryset:
            for tagged in tagged_list:
                if tagged.id == data.id:
                    object_list.append(tagged)
                    break
    except Tag.DoesNotExist:
        object_list = None

    info_dict = {
        'request': request,
        'tag': tag,
        'object_list': object_list,
    }
    return render_to_response('repository/tags_view.html', info_dict)

