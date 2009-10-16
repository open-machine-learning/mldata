"""
All custom repository logic is kept here
"""

import datetime, os, shutil
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.db import IntegrityError
from django.utils.translation import ugettext as _
from django.forms.util import ErrorDict
from repository.models import *
from repository.forms import *
from settings import MEDIA_URL


def _get_object_or_404(slug_or_id):
    obj = CurrentVersion.objects.filter(slug__text=slug_or_id)
    if not obj:
        obj = Data.objects.get(pk=slug_or_id)
        if not obj:
            raise Http404
    else:
        obj = obj[0].repository.data
    obj.slug_or_id = slug_or_id
    return obj


def index(request):
    try:
        latest_data = Data.objects.latest()
    except Data.DoesNotExist:
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


def data_index(request):
    object_list = CurrentVersion.objects.filter(type=TYPE['data']).order_by('-repository__pub_date')
    info_dict = {
        'user': request.user,
        'object_list': object_list,
    }
    return render_to_response('repository/data_index.html', info_dict)

def data_new(request):
    url = reverse(data_new)
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('auth_login') + '?next=' + url)

    if request.method == 'POST':
        form = DataForm(request.POST, request.FILES)
        if not request.FILES:
            d = ErrorDict({'': _('This field is required.')})
            form.errors['file'] = d.as_ul()
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
        form = DataForm(request.POST, request.FILES)
        if form.is_valid():
            next = form.save(commit=False)
            next.pub_date = datetime.datetime.now()
            next.slug_id = prev.slug_id
            next.version = next.get_next_version(type=TYPE['data'])
            next.author_id = request.user.id
            if request.FILES:
                next.file = request.FILES['file']
                next.file.name = next.get_filename()
            else:
                # this looks all fishy, but paths get mixed up somehow
                oldpath = prev.file.path # save old path, coz following copy is somewhat shallow
                next.file = prev.file
                next.file.name = next.get_filename()
                newpath = os.path.dirname(oldpath) + os.sep + next.file.name
                # for some unknown reason, next.file.name needs upload_to
                # prepended to be written properly into database...
                next.file.name = prev.file.field.upload_to + os.sep + next.file.name
                shutil.copyfile(oldpath, newpath)
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
    obj.versions = Data.objects.values('id', 'version').filter(slug__text=obj.slug.text).order_by('version')

    info_dict = {
        'object': obj,
        'user': request.user,
        'MEDIA_URL': MEDIA_URL,
    }
    return render_to_response('repository/data_view.html', info_dict)


def task_index(request):
    return render_to_response('repository/task_index.html')

def task_new(request):
    return render_to_response('repository/task_new.html')

def task_view(request, id):
    return render_to_response('repository/task_view.html')


def solution_index(request):
    return render_to_response('repository/solution_index.html')

def solution_new(request):
    return render_to_response('repository/solution_new.html')

def solution_view(request, id):
    return render_to_response('repository/solution_view.html')

