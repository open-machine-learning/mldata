from django.shortcuts import get_object_or_404, render_to_response
from about.models import About

def index(request):
#    obj = get_object_or_404(About, pk=1)
    return render_to_response('about/index.html', {
#        'obj': obj,
        'obj': '',
        })
