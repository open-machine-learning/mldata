from django.shortcuts import get_object_or_404, render_to_response
from about.models import About

def index(request):
    return render_to_response('about/index.html')

def impressum(request):
    return render_to_response('about/impressum.html')
