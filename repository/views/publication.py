from django.core import serializers
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from repository.forms import *
from repository.models import *


@transaction.commit_on_success
def edit(request):
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

def get(request, id):
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

