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
            new = Data()
            new.pub_date = datetime.datetime.now()
            new.name = form.cleaned_data['name']
            try:
                new.slug_id = new.get_slug_id(create=True)
            except IntegrityError:
                # looks quirky...
                from django.forms.util import ErrorDict
                d = ErrorDict({'':
                    _('The given name yields an already existing slug. Please try another name!')})
                form.errors['name'] = d.as_ul()
            else:
                new.version = 1
                new.summary = form.cleaned_data['summary']
                new.description = form.cleaned_data['description']
                new.urls = form.cleaned_data['urls']
                new.publications = form.cleaned_data['publications']
                new.license = form.cleaned_data['license']
                new.is_public = form.cleaned_data['is_public']
                new.author_id = request.user.id
                new.source = form.cleaned_data['source']
                new.format = form.cleaned_data['format']
                new.measurement_details = form.cleaned_data['measurement_details']
                new.usage_scenario = form.cleaned_data['usage_scenario']
                new.file = request.FILES['file']
                new.file.name = new.get_filename()
                new.tags = form.cleaned_data['tags']
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
            next = Data()
            next.pub_date = datetime.datetime.now()
            next.name = prev.name
            next.slug_id = next.get_slug_id()
            next.version = next.get_next_version(type=TYPE['data'])
            next.summary = form.cleaned_data['summary']
            next.description = form.cleaned_data['description']
            next.urls = form.cleaned_data['urls']
            next.publications = form.cleaned_data['publications']
            next.license = form.cleaned_data['license']
            next.is_public = form.cleaned_data['is_public']
            next.author_id = request.user.id
            next.source = form.cleaned_data['source']
            next.format = form.cleaned_data['format']
            next.measurement_details = form.cleaned_data['measurement_details']
            next.usage_scenario = form.cleaned_data['usage_scenario']
            next.file = request.FILES['file']
            next.file.name = next.get_filename()
            next.tags = form.cleaned_data['tags']
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

