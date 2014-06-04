import os
from django.core.mail import mail_admins
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.utils.translation import ugettext as _
from django.core.urlresolvers import reverse

from repository.models import *
from repository.forms import *

from preferences.models import Preferences

NUM_HISTORY_PAGE = 20
PER_PAGE_INTS = [10, 20, 50]

def get_versions_paginator(request, obj):
    """Get a paginator for item versions.

    @param request: request data
    @type request: Django request
    @param obj: item to get versions for
    @type obj: either class Data, Task or Method
    @return: paginator for item versions
    @rtype: Django paginator
    """
    items = obj.get_versions(request.user)
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


def get_tag_clouds(request):
    """Convenience function to retrieve tag clouds for all item types.

    @param request: request data
    @type request: Django request
    @return: list of tags with attributes font_size
    @rtype: hash with keys 'Data', 'Task', 'Method' containing lists of tagging.Tag
    """
    clouds = { 'Data': None, 'Task': None, 'Method': None, 'Challenge' : None}
    for k in clouds.iterkeys():
        klass = eval(k)
        clouds[k] = klass.get_tag_cloud(request.user)
    return clouds

###############################################################################
#
# PAGINATION
#

def get_per_page(count):
    PER_PAGE=[ p for p in PER_PAGE_INTS if p < count ]
    if not PER_PAGE:
        PER_PAGE.append(PER_PAGE_INTS[0])
    return PER_PAGE

def get_page(request, queryset, PER_PAGE):
    class dummy:
        pass

    try:
        klass=type(queryset[0])
    except:
        klass=dummy
        pass
    
    kname=klass.__name__.lower()

    perpage = PER_PAGE[0]
    try:
        perpage = int(request.GET.get('pp', PER_PAGE[0]))
    except:
        pass

    if perpage not in PER_PAGE_INTS:
        perpage = PER_PAGE[0]

    paginator = Paginator(queryset, perpage, allow_empty_first_page=True)

    page = request.GET.get(kname + '_page', 1)
    try:
        page_number = int(page)
    except ValueError:
        if page == 'last':
            page_number = paginator.num_pages
        else:
            # Page is not 'last', nor can it be converted to an int.
            paginator.page_obj = None
            return paginator
    try:
        page_obj = paginator.page(page_number)
    except InvalidPage:
        paginator.page_obj = None
        return paginator

    paginator.page_obj = page_obj
    if request.GET.has_key('data'):
        paginator.search_data=True
    if request.GET.has_key('task'):
        paginator.search_task=True
    if request.GET.has_key('method'):
        paginator.search_method=True
    if request.GET.has_key('challenge'):
        paginator.search_challenge=True
    return paginator

def get_upload_limit():
    return Preferences.objects.get(pk=1).max_data_size

def redirect_to_signin(next_link, kwargs):
    return HttpResponseRedirect(reverse('user_signin') + "?next=" + reverse(next_link, kwargs=kwargs))

def sendfile(fileobj, ctype):
    """Send given file to client.

    @param fileobj: file to send
    @type fileobj: File
    @param ctype: content type of file
    @type ctype: string
    @return: response
    @rtype: HTTPResponse
    @raise: Http404 on OSError
    """
    response = HttpResponse()
    response['Content-Type'] = ctype
    try:
        response['Content-Length'] = fileobj.size
        response['Content-Disposition'] = 'attachment; filename=' +\
            fileobj.name.split(os.sep)[-1]
        for chunk in fileobj.chunks():
            response.write(chunk)
    except OSError, e: # something wrong with file, maybe not existing
        mail_admins('Failed sending of file', str(e))
        raise Http404

    return response

def is_newer(first, second):
    """Check if second given file is newer than first given file.

    @param first: name of first file
    @type first: string
    @param second: name of second file
    @type second: string
    """
    stats_first = os.stat(first)
    stats_second = os.stat(second)
    # index 8 is last modified
    if stats_second[8] > stats_first[8]:
        return True
    else:
        return False
