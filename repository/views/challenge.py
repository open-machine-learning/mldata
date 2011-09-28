from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseForbidden, Http404
from django.core import serializers
from django.db import transaction

from repository.models import *
from repository.forms import *
from repository.views.util import *
import repository.views.base as base

def index(request, order_by='-pub_date'):
    """Index page of Challenge section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return base.index(request, Challenge, order_by=order_by)

def my(request):
    """My page of Challenge section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return base.index(request, Challenge, True)

def new(request):
    """New page of Challenge section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
@transaction.commit_on_success
def new(request, klass, default_arg=None):
    """Create a new item of given klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
    @return: user login page, item's view page or this page again on failed form validation
    @rtype: Django response
    @raise Http404: if given klass is unexpected
    """
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + request.path)

    if request.method == 'POST':
        form = ChallengeForm(request.POST, request.FILES, request=request)

        if form.is_valid():
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

                new.is_public = True

                new.license = FixedLicense.objects.get(pk=1) # fixed to CC-BY-SA
                new.save()
                new.task=form.cleaned_data['task']
                new.save()

                return HttpResponseRedirect(new.get_absolute_slugurl())
    else:
        form = formfunc(request=request)

    kname = Challenge.__name__.lower()

    info_dict = {
        'klass': klass.__name__,
        kname: True,
        'uuid': uuid.uuid4(), # for upload progress bar
        'url_new': request.path,
        'form': form,
        'request': request,
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
        'upload_limit': "%dMB" % (upload_limit / MEGABYTE)
    }

    return _response_for(request, klass, 'item_new', info_dict)

def view(request, id):
    """View Challenge item by id.

    @param request: request data
    @type request: Django request
    @param id: id of item to view
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.view(request, Challenge, id)

def view_slug(request, slug_challenge, version=None):
    """View page of Challenge section.

    @param request: request data
    @type request: Django request
    @param version: version of item to view
    @type version: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.view(request, Challenge, slug_challenge, version)

def edit(request, id):
    """Edit page of Challenge section.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.edit(request, Challenge, id)

def fork(request, id):
    """fork page of Challenge section.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.fork(request, Challenge, id)

def activate(request, id):
    """Activate of Challenge section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to activate
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.activate(request, Challenge, id)

def delete(request, id):
    """Delete of Challenge section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to delete
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.delete(request, Challenge, id)


def tags_view(request, tag):
    """View all items by given tag in Challenge.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    """
    return base.tags_view(request, tag, Challenge)

def rate(request, id):
    return base.rate(request, Challenge, id)

def score_download(request, slug):
    """Download of Challenge section.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: rendered response page
    @rtype: Django response
    """
    return base.download(request, Challenge, slug)

def get_tasks(request, id):
    """AJAX: Get tasks associated to challenge that is specified by id.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: integer
    @return: tasks in response page
    @rtype: Django response
    """
    qs_task=Task().get_public_qs(request.user)

    try:
        tasks=Challenge.objects.get(pk=id).get_tasks()
    except Challenge.DoesNotExist:
        tasks=Task.objects.all()

    data = serializers.serialize('json', tasks, fields=('name'))
    tasks = [ t.repository_ptr for t in tasks ]
    data = serializers.serialize('json', tasks, fields=('name'))

    return HttpResponse(data, mimetype='text/plain')
