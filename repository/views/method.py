import os

from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404
from django.core.files import File
from settings import CACHE_ROOT
import cPickle as pickle

from repository.models import *
from repository.forms import *
from repository.views.util import *
import repository.views.base as base
from repository.views.util import sendfile
import settings

def index(request, order_by='-pub_date'):
    """Index page of Method section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return base.index(request, Method, order_by=order_by)

def my(request):
    """My page of Method section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return base.index(request, Method, True)

def new(request):
    """New page of Method section.

    @param request: request data
    @type request: Django request
    @return: rendered response page
    @rtype: Django response
    """
    return base.new(request, Method)

def view(request, id):
    """View Method item by id.

    @param request: request data
    @type request: Django request
    @param id: id of item to view
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.view(request, Method, id)

def view_slug(request, slug_method, version=None):
    """View page of Method section.

    @param request: request data
    @type request: Django request
    @param slug_method: method slug of the item to view
    @type slug_method: string
    @param version: version of item to view
    @type version: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.view(request, Method, slug_method, version)

def edit(request, id):
    """Edit page of Method section.

    @param request: request data
    @type request: Django request
    @param id: id of item to edit
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.edit(request, Method, id)

def fork(request, id):
    """Fork page of Method section.

    @param request: request data
    @type request: Django request
    @param id: id of item to fork
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.fork(request, Method, id)

def activate(request, id):
    """Activate of Method section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to activate
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.activate(request, Method, id)

def delete(request, id):
    """Delete of Method section.

    @param request: request data
    @type request: Django request
    @param id: id of the item to delete
    @type id: integer
    @return: rendered response page
    @rtype: Django response
    """
    return base.delete(request, Method, id)


def tags_view(request, tag):
    """View all items by given tag in Method.

    @param request: request data
    @type request: Django request
    @param tag: name of the tag
    @type tag: string
    """
    return base.tags_view(request, tag, Method)

def rate(request, id):
    return base.rate(request, Method, id)

def score_download(request, slug):
    """Download of Method section.

    @param request: request data
    @type request: Django request
    @param slug: slug of item to downlaod
    @type slug: string
    @return: rendered response page
    @rtype: Django response
    """
    return base.download(request, Method, slug)

def plot_multiple_curves(request, id, resolution='medium'):
    method=get_object_or_404(Method, pk=id)
    results=Result.objects.filter(method=method)

    try:
        dpi=settings.RESOLUTIONS[resolution]
    except KeyError:
        raise Http404

    num_col=float(results.count())
    if num_col == 0.0:
        raise Http404

    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    #from matplotlib.backends.backend_cairo import FigureCanvasCairo as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib.cm import jet as col

    #legend=list()
    if dpi<=40:
        bgcol='#f7f7f7'
    else:
        bgcol='#ffffff'

    fig = Figure(figsize=(8,6), dpi=dpi, facecolor=bgcol)
    ax = fig.add_subplot(111)
    i=0.0

    for result in results:
        if result.complex_result_type!='Curve':
            raise Http404

        #legend.append(result.task.name)
        c=col((i+1)/num_col)
        i+=1

        r=pickle.loads(str(result.complex_result))
        x=r['x']
        y=r['y']
        x_name=r['x_name']
        y_name=r['y_name']
        ax.plot(x,y, alpha=0.5, marker='.', linewidth=5, color=c)
        #ax.plot(x,y,'rx',linewidth=1, alpha=0.9)
        #ax.bar(x,y)


    title=result.task.performance_measure + ' - auROC=%2.2f%%' % (100*result.aggregation_score)

    ax.set_title(title)
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.grid(True)
    ax.axis("tight")

    canvas = FigureCanvas(fig)
    response=HttpResponse(mimetype='image/png')
    canvas.print_png(response)
    return response

def plot_single_curve(request, id, resolution='tiny'):
    result=get_object_or_404(Result, pk=id)
    if result.complex_result_type!='Curve':
        raise Http404

    try:
        dpi=settings.RESOLUTIONS[resolution]
    except KeyError:
        raise Http404

    title=result.task.performance_measure + ' - auROC=%2.2f%%' % (100*result.aggregation_score)

    result=pickle.loads(str(result.complex_result))
    x=result['x']
    y=result['y']
    x_name=result['x_name']
    y_name=result['y_name']

    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    #from matplotlib.backends.backend_cairo import FigureCanvasCairo as FigureCanvas
    from matplotlib.figure import Figure

    if dpi<=40:
        bgcol='#f7f7f7'
    else:
        bgcol='#ffffff'
    fig = Figure(figsize=(8,6), dpi=dpi, facecolor=bgcol)
    ax = fig.add_subplot(111)


    ax.plot(x,y,'bo-', alpha=0.3, linewidth=5)
    #ax.plot(x,y,'rx',linewidth=1, alpha=0.9)
    #ax.bar(x,y)

    ax.set_title(title)
    ax.set_xlabel(x_name)
    ax.set_ylabel(y_name)
    ax.grid(True)
    ax.axis("tight")

    canvas = FigureCanvas(fig)
    response=HttpResponse(mimetype='image/png')
    canvas.print_png(response)
    return response

def get_predictions(request, id):
    """Extract the list of predictions from Result and return it"""
    print 'get_predictions', id
    obj = get_object_or_404(Result, pk=id)
    fname = obj.get_output_filename()
    fileobj = File(open(fname, 'r'))
    # create humanly readable export filename
    fname_export_visible = os.path.basename(fname)
    fileobj.name = fname_export_visible
    return sendfile(fileobj, 'text')
