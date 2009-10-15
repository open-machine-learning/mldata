"""
All custom repository logic is kept here
"""

import datetime
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from django.db import IntegrityError
from django.utils.translation import ugettext as _
from repository.models import *
from repository.forms import *
from settings import MEDIA_URL

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
    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseRedirect(reverse(data_index))

        form = DataForm(request.POST, request.FILES)
        if form.is_valid():
            new = form.save(commit=False)
            new.pub_date = datetime.datetime.now()
            try:
                new.slug_id = new.get_slug_id()
            except IntegrityError:
                # looks quirky...
                from django.forms.util import ErrorDict
                d = ErrorDict({'':
                    _('The given name yields an already existing slug. Please try another name!')})
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

    url_data_new = reverse(data_new)
    info_dict = {
        'form': form,
        'user': request.user,
        'submit': {
            'head': _('Submit new Data'),
            'action': url_data_new,
            'is_new': True,
            'title': _('New'),
        },
        'login': {
            'reason': _('submit new Data'),
            'next': url_data_new,
        },
    }
    return render_to_response('repository/data_submit.html', info_dict)

def data_edit(request, slug):
    prev = get_object_or_404(CurrentVersion, slug__text=slug).repository.data

    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseRedirect(reverse(data_index))

        request.POST['name'] = prev.name # cheat a little
        form = DataForm(request.POST, request.FILES)
        if form.is_valid():
            next = form.save(commit=False)
            next.pub_date = datetime.datetime.now()
            next.slug_id = prev.slug_id
            next.version = next.get_next_version(type=TYPE['data'])
            next.author_id = request.user.id
            next.file = request.FILES['file']
            next.file.name = next.get_filename()
            next.save(type=TYPE['data'])
            return HttpResponseRedirect(next.get_absolute_url())
    else:
        form = DataForm(instance=prev)

    url_data_edit = reverse(data_edit, args=[prev.slug.text])
    info_dict = {
        'form': form,
        'prev': prev,
        'user': request.user,
        'submit': {
            'head': _('Edit Data for') + ' ' + prev.name,
            'action': url_data_edit,
            'is_new': False,
            'title': _('Edit'),
        },
        'login': {
            'reason': _('edit Data'),
            'next': url_data_edit,
        },
    }
    return render_to_response('repository/data_submit.html', info_dict)

def data_view(request, slug):
    obj = get_object_or_404(CurrentVersion, slug__text=slug).repository.data
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

