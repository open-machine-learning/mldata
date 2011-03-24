from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404

import matplotlib
matplotlib.use('Cairo')
from matplotlib.figure import Figure
from matplotlib.backends.backend_cairo import FigureCanvasCairo as FigureCanvas
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from StringIO import StringIO

from repository.models import *
from repository.forms import *
from repository.views.util import *
import repository.views.base as base
import json

from  mleval import evaluation

def get_measures(request, type):
    """AJAX: Get measures associated with type
    """
    try:
        choices = evaluation.pm_hierarchy[type].keys()
    except KeyError:
        choices=[]
    choices.sort()
    data = json.dumps(choices)
    return HttpResponse(data, mimetype='text/plain')

def get_measure_help(request, type, name):
    """AJAX: Get measure help for type/name
    """
    try:
        helptxt = evaluation.pm_hierarchy[type][name][1]
    except KeyError:
        helptxt=[]
    data = json.dumps(helptxt)
    return HttpResponse(data, mimetype='text/plain')

def index(request, order_by='-pub_date', filter_type=None):
    return base.index(request, Task, order_by=order_by, filter_type=filter_type)

def my(request):
    return base.index(request, Task, True)

def new(request, cur_data=None):
    if cur_data:
        return base.new(request, Task, default_arg=cur_data)
    else:
        return base.new(request, Task)

def view(request, id, version=None):
    return base.view(request, Task, id)

def view_slug(request, slug_task, version=None):
    """View Task item by slug.
    """
    return base.view(request, Task, slug_task, version)

def edit(request, id):
    """Edit page of Task section.
    """
    return base.edit(request, Task, id)

def fork(request, id):
    """Fork page of Task section.
    """
    return base.fork(request, Task, id)

def delete(request, id):
    """Delete of Task section.
    """
    return base.delete(request, Task, id)

def activate(request, id):
    """Activate of Task section.
    """
    return base.activate(request, Task, id)

def download(request, slug):
    """Download of Task section.
    """
    return base.download(request, Task, slug)

def download_xml(request, slug):
    return base.download(request, Task, slug, 'xml')

def download_matlab(request, slug):
    return base.download(request, Task, slug, 'matlab')

def download_octave(request, slug):
    return base.download(request, Task, slug, 'octave')

def download_rdata(request, slug):
    return base.download(request, Task, slug, 'rdata')

#def predict(request, slug):
#    """AJAX: Evaluate results for Task given by id.
#    """
#    obj = Task.get_object(slug)
#    if not obj: raise Http404
#    if not obj.can_view(request.user):
#        return HttpResponseForbidden()
#
#    if 'qqfile' in request.FILES: # non-XHR style
#        indata = request.FILES['qqfile'].read()
#    else:
#        indata = request.raw_post_data
#    score, success = obj.predict(indata)
#
#    data = '{"score": "' + score + '", "success": "' + str(success) + '"}'
#    return HttpResponse(data, mimetype='text/plain')


def rate(request, id):
    return base.rate(request, Task, id)

def tags_view(request, tag):
    """View all items by given tag in Task.
    """
    return base.tags_view(request, tag, Task)

def task_rate(request, id):
    return base.rate(request, Task, id)


def plot_data_split_array(request,id):
    task=get_object_or_404(Task, pk=id)
    split_array=[]
    split_nr=0
    img = task.get_split_image(split_nr)
    while img!=None:
        split_array.append(img)
        split_nr+=1    
        img = task.get_split_image(split_nr)
        
    dpi=60
    bgcol='#ffffff'
    #fig = Figure(figsize=(7,0.3), dpi=dpi, facecolor=bgcol)

    fig = plt.figure( dpi=dpi, facecolor=bgcol)
    ax = fig.add_subplot(111)
    #canvas = FigureCanvas(fig)
    #ax.set_yticklabels([])
    ax.set_xticklabels([])
    #import pdb
    #pdb.set_trace()

    ax.imshow(split_array,aspect='auto',interpolation='nearest',cmap=cm.Greys)


    #plt.colorbar()
    imdata=StringIO()
    fig.savefig(imdata,format='png', dpi=dpi, facecolor=bgcol)
    return HttpResponse(imdata.getvalue(),mimetype='image/png')


def plot_data_split(request,id,split_nr):
    split_nr=int(split_nr)
    task=get_object_or_404(Task, pk=id)
    img = [task.get_split_image(split_nr)]
    #import pdb
    #pdb.set_trace()
    if (img == None):
        return None    

#   why it does not work ? 
    from pylab import axis
    axis('off')
    #import matplotlib
    #matplotlib.use('Cairo')
    #from matplotlib.figure import Figure
    #from matplotlib.backends.backend_cairo import FigureCanvasCairo as FigureCanvas
    #import matplotlib.cm as cm
    from StringIO import StringIO
    dpi=60
    bgcol='#ffffff'
    fig = Figure(figsize=(7,0.3), dpi=dpi, facecolor=bgcol)

#    fig = Figure( dpi=dpi, facecolor=bgcol)
    canvas = FigureCanvas(fig)
    bx = fig.add_subplot(111)
    bx.set_yticklabels([])
    bx.set_xticklabels([])
    #import pdb
    #pdb.set_trace()
    #mldata_col = {'red':((0,0,0),(0.1,0.1,0.1),(0.2,0.2,0.2)),'green':((0,0,0),(0.1,0.1,0.1),(0.2,0.2,0.2)),'blue':((0,0,0),(0.1,0.1,0.1),(0.2,0.2,0.2))}
    #mldata_cmap=matplotlib.colors.LinearSegmentedColormap('mldata_colormap',mldata_col,256)
    bx.imshow(img,aspect='auto',interpolation='nearest',cmap=cm.Greys)

#    bx = fig.add_subplot(212)
#    bx.set_yticklabels([])
#    bx.set_xticklabels([])

#    bx.imshow(img,aspect='auto',interpolation='nearest',cmap=cm.jet,extent=[0,len(img[0])-1,0,1])

    canvas.draw()
    imdata=StringIO()
    fig.savefig(imdata,format='png', dpi=dpi, facecolor=bgcol)
    return HttpResponse(imdata.getvalue(),mimetype='image/png')

