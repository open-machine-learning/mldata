"""
All custom repository logic is kept here
"""

import datetime
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from repository.models import *
from repository.forms import *
from settings import MEDIA_URL


class EmptyLatest:
    id = 0
    name = ''


def index(request):
    try:
        latest_data = Data.objects.latest()
    except Data.DoesNotExist:
        latest_data = EmptyLatest()
    try:
        latest_task = Task.objects.latest()
    except Task.DoesNotExist:
        latest_task = EmptyLatest()
    try:
        latest_solution = Solution.objects.latest()
    except Solution.DoesNotExist:
        latest_solution = EmptyLatest()

    info_dict = {
        'latest_data': latest_data,
        'latest_task': latest_task,
        'latest_solution': latest_solution,
    }
    return render_to_response('repository/index.html', info_dict)


def data_index(request):
    object_list = CurrentVersion.objects.all().order_by('-repository__pub_date')
    info_dict = {
        'object_list': object_list,
    }
    return render_to_response('repository/data_index.html', info_dict)

def data_new(request):
    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseRedirect(reverse('blog_index'))

        form = DataForm(request.POST, request.FILES)
        if form.is_valid():
            data = Data()
            data.pub_date = datetime.datetime.now()
            data.name = form.cleaned_data['name']
            data.version = 1
            data.summary = form.cleaned_data['summary']
            data.description = form.cleaned_data['description']
            data.urls = form.cleaned_data['urls']
            data.publications = form.cleaned_data['publications']
            data.license = form.cleaned_data['license']
            data.is_public = form.cleaned_data['is_public']
            data.author_id = request.user.id
            data.source = form.cleaned_data['source']
            data.format = form.cleaned_data['format']
            data.measurement_details = form.cleaned_data['measurement_details']
            data.usage_scenario = form.cleaned_data['usage_scenario']
            data.file = request.FILES['file']
            data.file.name = data.get_filename()
            data.tags = form.cleaned_data['tags']
            data.save()
            return HttpResponseRedirect(data.get_absolute_url())
    else:
        form = DataForm()

    info_dict = {
        'form': form,
        'user': request.user,
    }
    return render_to_response('repository/data_new.html', info_dict)

def data_edit(request, slug):
    try:
        prev = CurrentVersion.objects.filter(slug__text=slug)[0].repository.data
    except IndexError:
        raise Http404

    if request.method == 'POST':
        if not request.user.is_authenticated():
            return HttpResponseRedirect(reverse('blog_index'))

        request.POST['name'] = prev.name # cheat a little
        form = DataForm(request.POST, request.FILES)
        if form.is_valid():
            next = Data()
            next.pub_date = datetime.datetime.now()
            next.name = prev.name
            next.version = next.get_next_version()
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
            next.save()
            return HttpResponseRedirect(next.get_absolute_url())
    else:
        form = DataForm(instance=prev)

    info_dict = {
        'form': form,
        'prev': prev,
        'user': request.user,
    }
    return render_to_response('repository/data_edit.html', info_dict)

def data_view(request, slug):
    try:
        obj = CurrentVersion.objects.filter(slug__text=slug)[0].repository.data
    except IndexError:
        raise Http404
    info_dict = {
        'object': obj,
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

