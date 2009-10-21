"""
All custom repository logic is kept here
"""

import datetime, os, shutil
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.db import IntegrityError
from django.utils.translation import ugettext as _
from django.forms.util import ErrorDict
from repository.models import *
from repository.forms import *
from settings import MEDIA_URL


VERSIONS_PER_PAGE = 5
OBJECTS_PER_PAGE = 10


def _get_object_or_404(slug_or_id):
    obj = CurrentVersion.objects.filter(slug__text=slug_or_id).\
        filter(repository__is_deleted=False)
    if not obj:
        obj = Data.objects.get(pk=slug_or_id)
        if not obj or obj.is_deleted:
            raise Http404
    else:
        obj = obj[0].repository.data
    obj.slug_or_id = slug_or_id
    return obj


def _can_delete(user, author_id):
    if user.is_staff or user.is_superuser or user.id == author_id:
        return True
    else:
        return False


def index(request):
    try:
        latest_data = Data.objects.filter(is_deleted=False).order_by('-pub_date')[0]
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
        'user': request.user,
    }
    return render_to_response('repository/index.html', info_dict)


def _repository_index(request, type):
    objects = CurrentVersion.objects.filter(type=TYPE[type]).\
        filter(repository__is_deleted=False).order_by('-repository__pub_date')

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
        obj.get_absolute_url = getattr(obj.repository, type).get_absolute_url

    info_dict = {
        'user': request.user,
        'page': page,
        'type': type.capitalize(),
    }
    return render_to_response('repository/repository_index.html', info_dict)

def data_index(request):
    return _repository_index(request, 'data')
def task_index(request):
    return _repository_index(request, 'task')
def solution_index(request):
    return _repository_index(request, 'solution')



def data_new(request):
    url = reverse(data_new)
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('auth_login') + '?next=' + url)

    if request.method == 'POST':
        form = DataForm(request.POST, request.FILES)

        # manual validation coz it's required for new, but not edited data
        is_required = ErrorDict({'': _('This field is required.')}).as_ul()
        if not request.FILES:
            form.errors['file'] = is_required
        if not request.POST['format']:
            form.errors['format'] = is_required

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
                new.author_id = request.user.id
                new.file = request.FILES['file']
                new.file.name = new.get_filename()
                new.save(type=TYPE['data'])
                return HttpResponseRedirect(new.get_absolute_url())
    else:
        form = DataForm()

    info_dict = {
        'form': form,
        'user': request.user,
        'head': _('Submit new Data'),
        'action': url,
        'is_new': True,
        'title': _('New'),
    }
    return render_to_response('repository/data_submit.html', info_dict)


def data_edit(request, slug_or_id):
    prev = _get_object_or_404(slug_or_id)
    url = reverse(data_edit, args=[prev.slug_or_id])
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('auth_login') + '?next=' + url)

    if request.method == 'POST':
        request.POST['name'] = prev.name # cheat a little
        form = DataForm(request.POST)
        if form.is_valid():
            next = form.save(commit=False)
            next.pub_date = datetime.datetime.now()
            next.slug_id = prev.slug_id
            next.file = prev.file
            next.format = prev.format
            next.version = next.get_next_version(type=TYPE['data'])
            next.author_id = request.user.id
            next.save(type=TYPE['data'])
            return HttpResponseRedirect(next.get_absolute_url())
    else:
        form = DataForm(instance=prev)

    info_dict = {
        'form': form,
        'prev': prev,
        'user': request.user,
        'head': '%s %s (%s %s)' % \
            (_('Edit Data for'), prev.name, _('version'), prev.version),
        'action': url,
        'is_new': False,
        'title': _('Edit'),
    }
    return render_to_response('repository/data_submit.html', info_dict)


def data_view(request, slug_or_id):
    obj = _get_object_or_404(slug_or_id)

    obj.versions = Data.objects.values('id', 'version').\
        filter(slug__text=obj.slug.text).\
        filter(is_deleted=False).order_by('version')
    paginator = Paginator(obj.versions, VERSIONS_PER_PAGE)
    try:
        default_page = str((obj.version % VERSIONS_PER_PAGE) + 1)
        page = int(request.GET.get('page', default_page))
    except ValueError:
        page = 1
    try:
        obj.versions = paginator.page(page)
    except (EmptyPage, InvalidPage):
        obj.versions = paginator.page(paginator.num_pages)

    cv = CurrentVersion.objects.filter(slug__text=obj.slug.text)
    if cv[0].repository_id == obj.id:
        can_activate = False
    else:
        can_activate = True

    info_dict = {
        'object': obj,
        'user': request.user,
        'can_activate': can_activate,
        'can_delete': _can_delete(request.user, obj.author_id),
        'MEDIA_URL': MEDIA_URL,
    }
    return render_to_response('repository/data_view.html', info_dict)


def data_delete(request, slug_or_id):
    obj = _get_object_or_404(slug_or_id)
    if _can_delete(request.user, obj.author_id):
        obj.is_deleted = True
        current = Data.objects.filter(slug__text=obj.slug.text).\
            filter(is_deleted=False).order_by('-version')
        if current:
            cv = CurrentVersion.objects.filter(slug__text=obj.slug.text)
            if cv:
                cv[0].repository_id = current[0].id
                cv[0].save()
        obj.save(TYPE['data']) # a lil optimisation for db saves

    return HttpResponseRedirect(reverse(data_index))


def data_activate(request, id):
    if not request.user.is_authenticated():
        url=reverse(data_activate, args=[id])
        return HttpResponseRedirect(reverse('auth_login') + '?next=' + url)

    obj = get_object_or_404(Data, pk=id)
    cv = CurrentVersion.objects.filter(slug__text=obj.slug.text)
    if cv:
        cv[0].repository_id = obj.id
        cv[0].save()

    return HttpResponseRedirect(obj.get_absolute_url())


def task_new(request):
    url = reverse(data_new)
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('auth_login') + '?next=' + url)

    if request.method == 'POST':
        form = DataForm(request.POST, request.FILES)

        # manual validation coz it's required for new, but not edited data
        is_required = ErrorDict({'': _('This field is required.')}).as_ul()
        if not request.FILES:
            form.errors['file'] = is_required
        if not request.POST['format']:
            form.errors['format'] = is_required

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
                new.author_id = request.user.id
                new.file = request.FILES['file']
                new.file.name = new.get_filename()
                new.save(type=TYPE['data'])
                return HttpResponseRedirect(new.get_absolute_url())
    else:
        form = DataForm()

    info_dict = {
        'form': form,
        'user': request.user,
        'head': _('Submit new Data'),
        'action': url,
        'is_new': True,
        'title': _('New'),
    }
    return render_to_response('repository/data_submit.html', info_dict)


    return render_to_response('repository/task_new.html')

def task_view(request, slug_or_idid):
    return render_to_response('repository/task_view.html')

def task_edit(request, slug_or_id):
    return render_to_response('repository/task_view.html')


def solution_new(request):
    return render_to_response('repository/solution_new.html')

def solution_view(request, id):
    return render_to_response('repository/solution_view.html')

