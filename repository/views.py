"""
All custom repository logic is kept here
"""

import datetime, os
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.servers.basehttp import FileWrapper
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.db import IntegrityError, transaction
from django.utils.translation import ugettext as _
from django.forms.util import ErrorDict
from django.db.models import Q
from tagging.models import Tag, TaggedItem
from repository.models import *
from repository.forms import *
from settings import MEDIA_ROOT, TAG_SPLITSTR
from utils import hdf5conv


VERSIONS_PER_PAGE = 5
OBJECTS_PER_PAGE = 10



def index(request):
    qs = Q(is_deleted=False) & Q(is_public=True)
    latest = {}
    try:
        latest['data'] = Data.objects.filter(qs).order_by('-pub_date')[0]
    except IndexError:
        latest['data'] = None
    try:
        latest['task'] = Task.objects.filter(qs).order_by('-pub_date')[0]
    except IndexError:
        latest['task'] = None
    try:
        latest['solution'] = Solution.objects.filter(qs).order_by('-pub_date')[0]
    except IndexError:
        latest['solution'] = None

    info_dict = {
        'latest': latest,
        'request': request,
    }
    return render_to_response('repository/index.html', info_dict)



def _is_owner(request_user, obj_user):
    if request_user.is_staff or\
        request_user.is_superuser or\
        request_user == obj_user:
        return True
    else:
        return False


def _get_object_or_404(request, slug_or_id, klass):
    obj = CurrentVersion.objects.filter(slug__text=slug_or_id,
        repository__is_deleted=False)

    if obj: # slug + current version
        is_owner = _is_owner(request.user, obj[0].repository.user)
        if not is_owner and not obj[0].repository.is_public:
            raise Http404
        obj = getattr(obj[0].repository, klass.__name__.lower())
    else: # id
        try:
            obj = klass.objects.get(pk=slug_or_id)
        except klass.DoesNotExist:
            raise Http404
        if not obj or obj.is_deleted:
            raise Http404
        is_owner = _is_owner(request.user, obj.user)
        if not is_owner and not obj.is_public:
            raise Http404

    obj.is_owner = is_owner
    obj.slug_or_id = slug_or_id
    return obj


def _get_versions_paginator(request, obj):
    versions = obj.__class__.objects.values('id', 'version').\
        filter(slug__text=obj.slug.text).\
        filter(is_deleted=False).order_by('version')
    if not obj.is_owner:
        versions = versions.filter(is_public=True)
    paginator = Paginator(versions, VERSIONS_PER_PAGE)

    try:
        # dunno a better way than looping thru, since index != obj.version
        index = 0
        for v in versions:
            if v['id'] == obj.id:
                break
            else:
                index += 1
        default_page = (index / VERSIONS_PER_PAGE) + 1
        page = int(request.GET.get('page', str(default_page)))
    except ValueError:
        page = 1
    try:
        versions = paginator.page(page)
    except (EmptyPage, InvalidPage):
        versions = paginator.page(paginator.num_pages)

    return versions


def _get_completeness(obj):
    if obj.__class__ == Data:
        attrs = ['tags', 'description', 'license', 'summary', 'urls', 'publications', 'source', 'measurement_details', 'usage_scenario']
    elif obj.__class__ == Task:
        attrs = ['tags', 'description', 'license', 'summary', 'urls', 'publications', 'input', 'output', 'performance_measure', 'type', 'splits']
    elif obj.__class__ == Solution:
        attrs = ['tags', 'description', 'license', 'summary', 'urls', 'publications', 'feature_processing', 'parameters', 'os', 'code', 'score']
    else:
        return 0

    attrs_len = len(attrs)
    attrs_complete = 0
    for attr in attrs:
        if eval('obj.' + attr):
            attrs_complete += 1
    return int((attrs_complete * 100) / attrs_len)


def _get_rating_form(request, obj):
    rating_form = None
    if request.user.is_authenticated() and not request.user == obj.user:
        klass = eval(obj.__class__.__name__ + 'Rating')
        try:
            r = klass.objects.get(user__id=request.user.id, repository=obj)
            rating_form= RatingForm({
                'interesting': r.interesting,
                'documentation': r.documentation,
            })
        except klass.DoesNotExist:
            rating_form = RatingForm()
        rating_form.klassid = TYPE[obj.__class__.__name__]

    return rating_form


def _can_activate(obj):
    if not obj.is_owner:
        return False

    if not obj.is_public:
        return True

    try:
        cv = CurrentVersion.objects.get(slug=obj.slug)
        if not cv.repository_id == obj.id:
            return True
    except CurrentVersion.DoesNotExist:
        pass

    return False

@transaction.commit_on_success
def _activate(request, id, klass):
    if not request.user.is_authenticated():
        func = eval(klass.__name__.lower() + '_activate')
        url = reverse(func, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url)

    obj = get_object_or_404(klass, pk=id)
    if not _is_owner(request.user, obj.user):
        raise Http404

    obj.is_public = True
    obj.save()
    CurrentVersion.set(obj)

    return HttpResponseRedirect(obj.get_absolute_url(use_slug=True))


@transaction.commit_on_success
def _delete(request, slug_or_id, klass):
    obj = _get_object_or_404(request, slug_or_id, klass)
    if obj.is_owner:
        obj.is_deleted = True
        obj.save()
        current = klass.objects.filter(slug=obj.slug).\
            filter(is_deleted=False).order_by('-version')
        if current:
            CurrentVersion.set(current[0])

    func = eval(klass.__name__.lower() + '_my')
    return HttpResponseRedirect(reverse(func))


def _download(request, id, klass):
    obj = _get_object_or_404(request, id, klass)
    if klass == Data:
        fileobj = obj.file
    elif klass == Task:
        fileobj = obj.splits
    elif klass == Solution:
        fileobj = obj.score
    else:
        raise Http404

    # fails to work when OpenID Middleware is activated
#    filename = os.path.join(MEDIA_ROOT, fileobj.name)
#    wrapper = FileWrapper(file(filename))
#    response = HttpResponse(wrapper, content_type='application/octet-stream')
    # not sure if this alternative is a memory hog...
    response = HttpResponse()
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Length'] = fileobj.size
    response['Content-Disposition'] = 'attachment; filename=' + fileobj.name
    for chunk in fileobj.chunks():
        response.write(chunk)

    return response



def _view(request, slug_or_id, klass):
    obj = _get_object_or_404(request, slug_or_id, klass)
    if klass == Data and not obj.is_approved:
        return HttpResponseRedirect(reverse(data_new_review, args=[slug_or_id]))

    obj.completeness = _get_completeness(obj)
    obj.klass = klass.__name__
    # need tags in list
    obj.tags = obj.tags.split(TAG_SPLITSTR)
    obj.versions = _get_versions_paginator(request, obj)
    klassname = klass.__name__.lower()
    obj.url_activate = reverse(eval(klassname + '_activate'), args=[obj.id])
    obj.url_edit = reverse(eval(klassname + '_edit'), args=[obj.id])
    obj.url_delete = reverse(eval(klassname + '_delete'), args=[obj.id])

    info_dict = {
        'object': obj,
        'request': request,
        'can_activate': _can_activate(obj),
        'can_delete': obj.is_owner,
        'rating_form': _get_rating_form(request, obj),
    }
    if klass == Data:
        info_dict['extract'] = hdf5conv.get_extract(
            os.path.join(MEDIA_ROOT, obj.file.name))

    return render_to_response('repository/item_view.html', info_dict)



@transaction.commit_on_success
def _new(request, klass):
    url_new = reverse(eval(klass.__name__.lower() + '_new'))
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('user_signin') + '?next=' + url_new)

    if request.method == 'POST':
        if klass == Data:
            form = DataForm(request.POST, request.FILES)
        elif klass == Task:
            form = TaskForm(request.POST, request.FILES, request=request)
        elif klass == Solution:
            form = SolutionForm(request.POST, request.FILES, request=request)
        else:
            raise Http404

        # manual validation coz it's required for new, but not edited item
        if not request.FILES:
            if klass == Data:
                form.errors['file'] = ErrorDict({'': _('This field is required.')}).as_ul()
            elif klass == Task or klass == Solution:
                pass
            else:
                raise Http404

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
                # set to invisible for public until activated / made public
                new.is_public = False
                new.user = request.user

                if klass == Data:
                    new.file = request.FILES['file']
                    new.format = hdf5conv.get_fileformat(request.FILES['file'].name)
                    new.file.name = new.get_filename()
                    new.save()
                    func = eval(klass.__name__.lower() + '_new_review')
                elif klass == Task:
                    if 'splits' in request.FILES:
                        new.splits = request.FILES['splits']
                        new.splits.name = new.get_splitname()
                    new.save()
                    form.save_m2m() # a bit odd
                    CurrentVersion.set(new)
                    func = eval(klass.__name__.lower() + '_view')
                elif klass == Solution:
                    if 'score' in request.FILES:
                        new.score = request.FILES['score']
                        new.score.name = new.get_scorename()
                    new.save()
                    CurrentVersion.set(new)
                    func = eval(klass.__name__.lower() + '_view')
                else:
                    raise Http404
                return HttpResponseRedirect(reverse(func, args=[new.id]))
    else:
        if klass == Data:
            form = DataForm()
        elif klass == Task:
            form = TaskForm(request=request)
        elif klass == Solution:
            form = SolutionForm(request=request)
        else:
            raise Http404

    info_dict = {
        'klass': klass.__name__,
        'url_new': url_new,
        'form': form,
        'request': request,
    }

    return render_to_response('repository/item_new.html', info_dict)



@transaction.commit_on_success
def _edit(request, slug_or_id, klass):
    prev = _get_object_or_404(request, slug_or_id, klass)
    prev.klass = klass.__name__
    prev.url_edit = reverse(
        eval(klass.__name__.lower() + '_edit'), args=[prev.id])
    if not request.user.is_authenticated():
        return HttpResponseRedirect(
            reverse('user_signin') + '?next=' + prev.url_edit)

    if request.method == 'POST':
        request.POST['name'] = prev.name # cheat a little

        if klass == Data:
            form = DataForm(request.POST)
        elif klass == Task:
            form = TaskForm(request.POST, request=request)
        elif klass == Solution:
            form = SolutionForm(request.POST, request=request)
        else:
            raise Http404

        if form.is_valid():
            next = form.save(commit=False)
            next.pub_date = datetime.datetime.now()
            next.slug_id = prev.slug_id
            next.version = next.get_next_version()
            next.user_id = request.user.id
            if klass == Data:
                next.format = prev.format
                next.is_approved = prev.is_approved
                next.file = prev.file
                next.save()
            elif klass == Task:
                if 'splits' in request.FILES:
                    next.splits = request.FILES['splits']
                    next.splits.name = next.get_splitname()
                    filename = os.path.join(MEDIA_ROOT, prev.splits.name)
                    if os.path.isfile(filename):
                        os.remove(filename)
                else:
                    next.splits = prev.splits
                next.save()
                form.save_m2m() # a bit odd
            elif klass == Solution:
                if 'score' in request.FILES:
                    next.score = request.FILES['score']
                    next.score.name = next.get_scorename()
                    filename = os.path.join(MEDIA_ROOT, prev.score.name)
                    if os.path.isfile(filename):
                        os.remove(filename)
                else:
                    next.score = prev.score
                next.save()
            else:
                raise Http404
            CurrentVersion.set(next)
            return HttpResponseRedirect(next.get_absolute_url(True))
    else:
        if klass == Data:
            form = DataForm(instance=prev)
        elif klass == Task:
            form = TaskForm(instance=prev, request=request)
        elif klass == Solution:
            form = SolutionForm(instance=prev, request=request)
        else:
            raise Http404

    info_dict = {
        'form': form,
        'object': prev,
        'request': request,
    }

    return render_to_response('repository/item_edit.html', info_dict)



def _index(request, klass, my=False):
    objects = CurrentVersion.objects.filter(
        type=TYPE[klass.__name__],
        repository__is_deleted=False
    ).order_by('-repository__pub_date')

    if my:
        objects = objects.filter(repository__user=request.user)
        if klass == Data:
            unapproved = klass.objects.filter(
                user=request.user,
                is_approved=False
            )
        else:
            unapproved = None
        my_or_archive = _('My')
    else:
        objects = objects.filter(repository__is_public=True)
        unapproved = None
        my_or_archive = _('Public Archive')

    paginator = Paginator(objects, OBJECTS_PER_PAGE)
    try:
        num = int(request.GET.get('page', '1'))
    except ValueError:
        num = 1
    try:
        page = paginator.page(num)
    except (EmptyPage, InvalidPage):
        page = paginator.page(paginator.num_pages)

    # quirky, but simplifies templates
    for obj in page.object_list:
        obj.absolute_url = getattr(obj.repository, klass.__name__.lower()).\
            get_absolute_url(use_slug=True)

    info_dict = {
        'request': request,
        'page': page,
        'klass': klass.__name__,
        'unapproved': unapproved,
        'my_or_archive': my_or_archive,
    }
    return render_to_response('repository/item_index.html', info_dict)


def data_index(request):
    return _index(request, Data)
def data_my(request):
    return _index(request, Data, True)
def data_view(request, slug_or_id):
    return _view(request, slug_or_id, Data)
def data_delete(request, slug_or_id):
    return _delete(request, slug_or_id, Data)
def data_activate(request, id):
    return _activate(request, id, Data)
def data_download(request, id):
    return _download(request, id, Data)
def data_new(request):
    return _new(request, Data)
def data_edit(request, slug_or_id):
    return _edit(request, slug_or_id, Data)

def task_index(request):
    return _index(request, Task)
def task_my(request):
    return _index(request, Task, True)
def task_view(request, slug_or_id):
    return _view(request, slug_or_id, Task)
def splits_download(request, id):
    return _download(request, id, Task)
def task_activate(request, id):
    return _activate(request, id, Task)
def task_delete(request, slug_or_id):
    return _delete(request, slug_or_id, Task)
def task_new(request):
    return _new(request, Task)
def task_edit(request, slug_or_id):
    return _edit(request, slug_or_id, Task)

def solution_index(request):
    return _index(request, Solution)
def solution_my(request):
    return _index(request, Solution, True)
def solution_view(request, slug_or_id):
    return _view(request, slug_or_id, Solution)
def score_download(request, id):
    return _download(request, id, Solution)
def solution_activate(request, id):
    return _activate(request, id, Solution)
def solution_delete(request, slug_or_id):
    return _delete(request, slug_or_id, Solution)
def solution_new(request):
    return _new(request, Solution)
def solution_edit(request, slug_or_id):
    return _edit(request, slug_or_id, Solution)



@transaction.commit_on_success
def data_new_review(request, id):
    if not request.user.is_authenticated():
        next = '?next=' + reverse(data_new_review, args=[id])
        return HttpResponseRedirect(reverse('user_signin') + next)

    obj = _get_object_or_404(request, id, Data)
    # don't want users to be able to remove items once approved
    if obj.is_approved:
        raise Http404

    if request.method == 'POST':
        if request.POST.has_key('revert'):
            os.remove(os.path.join(MEDIA_ROOT, obj.file.name))
            obj.delete()
            return HttpResponseRedirect(reverse(data_new))
        elif request.POST.has_key('approve'):
            uploaded = os.path.join(MEDIA_ROOT, obj.file.name)
            converted = hdf5conv.get_filename(uploaded)

            format = request.POST['id_format'].lower()
            if format != 'hdf5':
                try:
                    hdf5conv.convert(uploaded, format, converted, 'hdf5')
                    format = 'hdf5'
                except Exception:
                    pass
            obj.format = format

            if os.path.isfile(converted): # assign converted file to obj
                os.remove(uploaded)
                # for some reason, FileField saves file.name as DATAPATH/<basename>
                obj.file.name = os.path.sep.join([DATAPATH, converted.split(os.path.sep)[-1]])

            obj.is_approved = True
            obj.save()
            CurrentVersion.set(obj)
            return HttpResponseRedirect(reverse(data_view, args=[obj.id]))

    info_dict = {
        'object': obj,
        'request': request,
        'extract': hdf5conv.get_extract(os.path.join(MEDIA_ROOT, obj.file.name)),
    }
    return render_to_response('repository/data_new_review.html', info_dict)



def tags_index(request):
    current = CurrentVersion.objects.filter(
            Q(repository__user=request.user.id) | Q(repository__is_public=True)
    )
    if current:
        all = Tag.objects.all()
        tags = []
        for tag in all:
            found = False
            tag.count = 0
            for item in tag.items.values():
                for object in current:
                    if item['object_id'] == object.repository.id:
                        found = True
                        tag.count += 1
            if found:
                tags.append(tag)
    else:
        tags = None

    info_dict = {
        'request': request,
        'tags': tags,
    }
    return render_to_response('repository/tags_index.html', info_dict)


def tags_view(request, tag):
    try:
        current = CurrentVersion.objects.filter(
                Q(repository__user=request.user.id) | Q(repository__is_public=True)
        )
        tag = Tag.objects.get(name=tag)
        tagged = TaggedItem.objects.filter(tag=tag)
        objects = []
        for c in current:
            for t in tagged:
                if t.object_id == c.repository.id:
                    try:
                        o = c.repository.data
                    except:
                        try:
                            o = c.repository.task
                        except:
                            try:
                                o = c.repository.solution
                            except:
                                raise Http404
                    objects.append(o)
                    break
    except Tag.DoesNotExist:
        objects = None

    info_dict = {
        'request': request,
        'tag': tag,
        'objects': objects,
    }
    return render_to_response('repository/tags_view.html', info_dict)



def rate(request, klassid, id):
    try:
        inverted = dict((v,k) for k, v in TYPE.iteritems())
        klassname = inverted[int(klassid)]
    except KeyError: # user tries nasty things
        raise Http404
    else:
        rklass = eval(klassname + 'Rating')
        klass = eval(klassname)

    obj = get_object_or_404(klass, pk=id)
    if request.user.is_authenticated() and not request.user == obj.user:
        if request.method == 'POST':
            form=RatingForm(request.POST)
            if form.is_valid():
                r, fail = rklass.objects.get_or_create(user=request.user, repository=obj)
                r.update_rating(
                    form.cleaned_data['interesting'],
                    form.cleaned_data['documentation'],
                )

    return HttpResponseRedirect(obj.get_absolute_url())
