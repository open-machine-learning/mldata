from django.shortcuts import get_object_or_404, render_to_response
from hello.models import Hello

def index(request):
    obj = get_object_or_404(Hello, pk=1)
    return render_to_response('hello/index.html', {
        'obj': obj,
        })
