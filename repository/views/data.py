from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from repository.models import *
from repository.forms import *

from settings import TAG_SPLITSTR

import repository

from repository.views.util import *
from repository.views.util import MEGABYTE

############################################################################
#
# Main index
#

def index(request):
    objects = Data.get_public_active_objects().order_by('-pub_date')

    PER_PAGE = get_per_page(objects.count())
    
    info_dict = {
        'request': request,
        'page': get_page(request, objects, PER_PAGE),
        'searcherror': None,
        'klass': 'Data',
        'unapproved': None,
        'my_or_archive': _('Public Archive'),
        'per_page': PER_PAGE,
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
    }

    return render_to_response('data/item_index.html', info_dict)

def my(request, id):
    objects = Data.get_public_active_objects.order_by('-pub_date')

    if request.user.is_authenticated():
        objects = objects.filter(user=request.user).order_by('slug')
        unapproved = Data.objects.filter(user=request.user, is_approved=False)

    PER_PAGE = _get_per_page(objects.count())

    info_dict = {
        'request': request,
        'page': _get_page(request, objects, PER_PAGE),
        'searcherror': searcherror,
        'klass': Data.__name__,
        'unapproved': unapproved,
        'my_or_archive': _('My'),
        'per_page': PER_PAGE,
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
    }

    return render_to_response('data/item_index.html', info_dict)

#############################################################################
#
# Viewing data objects
#

def view(request, slug_or_id, version=None):
    """View data item
    """

    obj = Data.get_object(slug_or_id, version)
    if not obj: raise Http404
    if not obj.can_view(request.user):
        return HttpResponseForbidden()

    if not obj.is_approved:
        return HttpResponseRedirect(reverse(new_review, args=[obj.slug]))

    current = Data.objects.get(slug=obj.slug, is_current=True)
    current.hits += 1
    current.save()

    tags = obj.tags.split(TAG_SPLITSTR)
    versions = get_versions_paginator(request, obj)
    url_activate = reverse(repository.views.data.activate, args=[obj.id])
    url_edit = reverse(repository.views.data.edit, args=[obj.id])
    url_delete = reverse(repository.views.data.delete, args=[obj.id])

    obj.has_h5()

    extract = obj.get_extract()

    info_dict = {
        'object': obj,
        'request': request,
        'can_activate': obj.can_activate(request.user),
        'can_delete': obj.can_delete(request.user),
        'current': current,
        'rating_form': RatingForm.get(request, obj),
        'tagcloud': get_tag_clouds(request),
        'related': obj.filter_related(request.user),
        'klass': Data,
        'section': 'repository',
        'extract': extract,
        'url_activate': url_activate,
        'url_edit': url_edit,
        'url_delete': url_delete,
        'tags': tags,
        'versions': versions
    }

    return render_to_response('data/item_view.html', info_dict)

def view_slug(request, slug, version=None):
    return view(request, slug, version)

#############################################################################
#
# Creation, Editing, etc.
#

@transaction.commit_on_success
def new(request):
    """Create a new Data item.
    """
    url_new = reverse('repository.views.data.new')
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url_new)

    formfunc = DataForm
    upload_limit = get_upload_limit()
    if request.method == 'POST':
        request.upload_handlers.insert(0, UploadProgressCachedHandler(request=request))
        form = formfunc(request.POST, request.FILES, request=request)

        # manual validation coz it's required for new, but not edited Data
        if not request.FILES:
            form.errors['file'] = ErrorDict({'': _('This field is required.')}).as_ul()

        # check whether file is too large
        if len(request.FILES['file']) > upload_limit:
             form.errors['file'] = ErrorDict({'': _('File is too large!  Must be smaller than %dMB!' % (upload_limit / MEGABYTE))}).as_ul()

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

                if not form.cleaned_data['keep_private']:
                    new.is_public = True

                new.file = request.FILES['file']
                new.num_instances = -1
                new.num_attributes = -1
                new.save()

                # InMemoryUploadedFile returns file-like object whereas
                # zipfile/tarfile modules used in get_uncompressed() require
                # filename (prior to python 2.7), so we have to save it to
                # disk, then rename, then save object again.
                name_old = os.path.join(MEDIA_ROOT, new.file.name)
                uncompressed = ml2h5.data.get_uncompressed(name_old)
                if uncompressed:
                    os.remove(name_old)
                    name_old = uncompressed

                new.format = ml2h5.fileformat.get(name_old)
                name_new = os.path.join(DATAPATH, new.get_filename())
                os.rename(name_old, os.path.join(MEDIA_ROOT, name_new))
                new.file.name = name_new
                new.save()
                return HttpResponseRedirect(new.get_absolute_slugurl())
    else:
        form = formfunc(request=request)

    info_dict = {
        'klass': Data.__name__,
        'uuid': uuid.uuid4(), # for upload progress bar
        'url_new': url_new,
        'form': form,
        'request': request,
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
        'upload_limit': "%dMB" % (upload_limit / MEGABYTE)
    }

    return render_to_response('data/item_new.html', info_dict)

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
        return redirect_to_signin('repository.views.data.new_review', args=[slug])

    obj = Data.get_object(slug)
    if not obj: raise Http404
    # don't want users to be able to remove items once approved
    if not obj.can_edit(request.user) or obj.is_approved:
        return HttpResponseForbidden()

    fname = os.path.join(MEDIA_ROOT, obj.file.name)
    form = None
    if request.method == 'POST':
        if request.POST.has_key('revert'):
            os.remove(fname)
            obj.delete()
            return HttpResponseRedirect(reverse(data_new))
        elif request.POST.has_key('approve'):
            form = DataReviewForm(request.POST)
            if form.is_valid():
                try:
                    obj.approve(fname, form.cleaned_data)
                except ml2h5.converter.ConversionError, error:
                    url = 'http://' + request.META['HTTP_HOST'] + reverse(
                        data_view_slug, args=[obj.slug])
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

@transaction.commit_on_success
def edit(request, id):
    """Edit existing item given by slug or id and Data.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param id: id of the item to activate
    @type id: integer
    @return: user login page, item's view page or this page again on failed form validation
    @rtype: Django response
    @raise Http404: if item couldn't be found or given klass is unexpected
    """
    prev = Data.get_object(id)
    if not prev: raise Http404
    prev.klass = 'Data'
    prev.url_edit = reverse(edit, args=[prev.id])
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + prev.url_edit)
    if not prev.can_edit(request.user):
        return HttpResponseForbidden()

    formfunc = eval('DataForm')
    if request.method == 'POST':
        request.POST['name'] = prev.name # cheat a little
        form = formfunc(request.POST, request=request)

        if form.is_valid():
            next = form.save(commit=False)
            next.pub_date = datetime.datetime.now()
            next.slug = prev.slug
            next.version = next.get_next_version()
            next.user = request.user

            if prev.is_public: # once public, always public
                next.is_public = True
            elif not form.cleaned_data['keep_private']:
                next.is_public = True

            next.format = prev.format
            next.is_approved = prev.is_approved
            next.file = prev.file
            next.save()

            form.save_m2m() # for publications
            Data.set_current(next.slug)
            return HttpResponseRedirect(next.get_absolute_slugurl())
    else:
        form = formfunc(instance=prev, request=request)

    info_dict = {
        'form': form,
        'object': prev,
        'request': request,
        'publication_form': PublicationForm(),
        'tagcloud': get_tag_clouds(request),
        'section': 'repository',
    }

    return render_to_response('data/item_edit.html', info_dict)

@transaction.commit_on_success
def delete(request, id):
    """Delete data item specified by id
    """
    if not request.user.is_authenticated():
        url = reverse(delete, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = Data.get_object(id)
    if not obj: raise Http404
    if not obj.can_delete(request.user):
        return HttpResponseForbidden()
    obj.is_deleted = True
    obj.save()

    current = Data.set_current(obj.slug)
    if current:
        return HttpResponseRedirect(current.get_absolute_slugurl())

    return HttpResponseRedirect(reverse(my))

@transaction.commit_on_success
def activate(request, Data, id):
    """Activate data item by id
    """
    if not request.user.is_authenticated():
        url = reverse(activate, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = Data.get_object(id)
    if not obj: raise Http404
    if obj.can_activate(request.user):
        obj.is_public = True
        obj.save()
        Data.set_current(obj.slug)

    return HttpResponseRedirect(obj.get_absolute_slugurl())

#############################################################################
#
# Downloading
#

def download(request, slug, type='plain'):
    """Download file relating to item given by id and klass and possibly type.
    """
    obj = Data.get_object(slug)
    if not obj: raise Http404
    if not obj.can_download(request.user):
        return HttpResponseForbidden()

    fname_export = None
    fileobj = obj.file
    fname = obj.file.name
    format = ml2h5.fileformat.get(os.path.join(MEDIA_ROOT, fname))

    if type == 'plain':
        if format == 'h5':
            ctype = 'application/x-hdf'
        else:
            ctype = 'application/octet-stream'

    else:
        if not fileobj: # maybe no file attached to this item
            raise Http404
        if format != 'h5': # only convert h5 files
            raise Http404
        fname_h5 = os.path.join(MEDIA_ROOT, obj.file.name)
        fname_export = fname_h5 + '.' + type

        if type == 'xml':
            if not os.path.exists(fname_export) or _is_newer(fname_export, fname_h5):
                cmd = 'h5dump --xml ' + fname_h5 + ' > ' + fname_export
                if not subprocess.call(cmd, shell=True) == 0:
                    mail_admins('Download: Failed conversion of %s to XML' % (fname_h5), cmd)
                    raise Http404
        elif type in ('csv', 'arff', 'libsvm', 'matlab', 'octave'):
            if not os.path.exists(fname_export) or _is_newer(fname_export, fname_h5):
                try:
                    c = ml2h5.converter.Converter(fname_h5, fname_export, format_out=type)
                    c.run()
                except ml2h5.converter.ConversionError, e:
                    subject = 'Download: Failed conversion of %s to %s' % (fname_h5, type)
                    body = traceback.format_exc() + "\n" + str(e)
                    mail_admins(subject, body)
                    raise Http404
        else:
            raise Http404

        if type == 'matlab':
            ctype = 'application/x-matlab'
        else:
            ctype = 'application/' + type
        fileobj = File(open(fname_export, 'r'))

    if not fileobj: # something went wrong
        raise Http404

    response = sendfile(fileobj, ctype)

    fileobj.close()
    if fname_export: # remove exported file
        os.remove(fname_export)
    obj.increase_downloads()
    return response

def download_xml(request, id):
    return download(request, id, 'xml')

def download_csv(request, id):
    return download(request, id, 'csv')

def download_arff(request, id):
    return download(request, id, 'arff')

def download_libsvm(request, id):
    return download(request, id, 'libsvm')

def download_matlab(request, id):
    return download(request, id, 'matlab')

def download_octave(request, id):
    return download(request, id, 'octave')

def rate(request, id):
    """Rate an item given by id and klass.

    @param request: request data
    @type request: Django request
    @param klass: item's class for lookup in correct database table
    @type klass: either Data, Task or Solution
    @param id: item's id
    @type id: integer
    @return: redirect to item's view page
    @rtype: Django response
    @raise Http404: if item could not be found
    """
    if not request.user.is_authenticated():
        url = reverse(activate, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = Data.get_object(id)
    if not obj: raise Http404
    rklass = eval(Data.__name__ + 'Rating')
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            r, fail = rklass.objects.get_or_create(user=request.user, repository=obj)
            r.update(form.cleaned_data['interest'], form.cleaned_data['doc'])

    return HttpResponseRedirect(obj.get_absolute_slugurl())

