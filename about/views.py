from django.shortcuts import get_object_or_404, render_to_response
from django.contrib.auth.models import User

def index(request):
    return render_to_response('about/index.html', {'user': request.user})

def impressum(request):
    return render_to_response('about/impressum.html', {'user': request.user})

def tos(request):
    return render_to_response('about/tos.html', {'user': request.user})
