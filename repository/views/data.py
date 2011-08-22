from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from repository.forms import *
from repository.models import *
from repository.views.util import *
import traceback
from django.db import transaction

import repository.views.base as base
from settings import MEDIA_ROOT, DATAPATH
import ml2h5.fileformat

############################################################################
#
# Main index
#

def index(request, order_by='-pub_date'):
    return base.index(request, Data, order_by=order_by)

def my(request):
    return base.index(request, Data, True)

#############################################################################
#
# Viewing data objects
#

def view(request, id, version=None):
    return base.view(request, Data, id)

def view_slug(request, slug, version=None):
    return base.view(request, Data, slug, version)

#############################################################################
#
# Creation, Editing, etc.
#

def new(request):
    """Create a new Data item.
    """
    return base.new(request, Data)

@transaction.commit_on_success
def new_review(request, slug):
    """Review Data item to check if uploaded file is as expected.

    @param request: request data
    @type request: Django request
    @param slug: slug of the item to review
    @type slug: string
    @return: redirect user to login page or item's view page after approval or review form
    @rtype: Django response
    @raise Http404: if item couldn't be found
    """
    if not request.user.is_authenticated():
        return redirect_to_signin('repository.views.data.new_review', kwargs={'slug' : slug})

    obj = Data.get_object(slug)
    if not obj: raise Http404
    # don't want users to be able to remove items once approved
    if not obj.can_edit(request.user) or (obj.is_approved and obj.is_public):
        return HttpResponseForbidden()

    dummy, ext = os.path.splitext(obj.file.name)
    fname = os.path.join(MEDIA_ROOT, DATAPATH, '%s%s' % (slug, ext))
    form = None
    if request.method == 'POST':
        if request.POST.has_key('revert'):
            try:
                os.remove(fname)
            except:
                pass
            obj.delete()
            return HttpResponseRedirect(reverse(new))
        elif request.POST.has_key('approve'):
            form = DataReviewForm(request.POST)
            if form.is_valid():
                try:
                    obj.approve(fname, form.cleaned_data)
                except ml2h5.converter.ConversionError, error:
                    url = 'http://' + request.META['HTTP_HOST'] + reverse(
                        view_slug, args=[obj.slug])
                    subject = 'Failed conversion to HDF5: %s' % url
                    body = "Hi admin!\n\n" +\
                        'URL: ' + url + "\n\n" +\
                        traceback.format_exc() + "\n" + str(error)
                    mail_admins(subject, body)
                return HttpResponseRedirect(
                    reverse(view_slug, args=[obj.slug]))

    if not form:
        form = DataReviewForm()
        form.prefill(obj.format, ml2h5.fileformat.infer_seperator(fname))

    info_dict = {
        'object': obj,
        'form': form,
        'request': request,
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
        'supported_formats': ', '.join(ml2h5.converter.HANDLERS.iterkeys()),
        'extract': ml2h5.data.get_extract(fname),
    }
    return render_to_response('data/data_new_review.html', info_dict)

def edit(request, id):
    return base.edit(request, Data, id)

def fork(request, id):
    """Fork page of Data section.

    @param request: request data
    @type request: Django request
    @param id: id of item to fork
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.fork(request, Data, id)

def delete(request, id):
    """Delete data item specified by id
    """
    return base.delete(request, Data, id)

def activate(request, id):
    """Activate data item by id
    """
    return base.activate(request, Data, id)

#############################################################################
#
# Downloading
#

def download(request, slug):
    """Download file relating to item given by slug and klass and possibly type.
    """
    return base.download(request, Data, slug)

def download_xml(request, slug):
    return base.download(request, Data, slug, 'xml')

def download_csv(request, slug):
    return base.download(request, Data, slug, 'csv')

def download_arff(request, slug):
    return base.download(request, Data, slug, 'arff')

def download_libsvm(request, slug):
    return base.download(request, Data, slug, 'libsvm')

def download_matlab(request, slug):
    return base.download(request, Data, slug, 'matlab')

def download_octave(request, slug):
    return base.download(request, Data, slug, 'octave')

def download_rdata(request, slug):
    return base.download(request, Data, slug, 'rdata')

def rate(request, id):
    """Rate an item given by id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Method
    @param id: item's id
    @type id: integer
    @return: redirect to item's view page
    @rtype: Django response
    @raise Http404: if item could not be found
    """
    return base.rate(request, Data, id)

def tags_view(request, tag):
    """View all items by given tag in Data.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    """
    return base.tags_view(request, tag, Data)

def data_rate(request, id):
    return base.rate(request, Data, id)
