from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.models import User

def index(request):
    return render_to_response('about/index.html', {'request': request})

def impressum(request):
    return render_to_response('about/impressum.html', {'request': request})

def tos(request):
    return render_to_response('about/tos.html', {'request': request})
