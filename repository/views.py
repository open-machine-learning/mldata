"""
All custom repository logic is kept here
"""

import datetime
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from repository.models import *
from utils import slugify
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
    object_list = Data.objects.all()
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
            data.version = 1
            data.name = form.cleaned_data['name']
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
            data.file.name = slugify(data.name) + '%s' % (data.version)
            data.save()
            return HttpResponseRedirect(data.get_absolute_url())
    else:
        form = DataForm()

    info_dict = {
        'form': form,
        'user': request.user,
    }
    return render_to_response('repository/data_new.html', info_dict)

def data_view(request, id):
    obj = get_object_or_404(Data, pk=id, is_public=True)
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

