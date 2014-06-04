from django.core.cache import cache
from django.http import HttpResponse
from django.http import HttpResponseServerError
from django.utils import simplejson


def upload_progress(request):
    """Return JSON object with information about the progress of an upload.

    @param request: request data
    @type request: Django request
    @return: progress information
    @rtype: Django response
    """
    progress_id = ''
    if 'X-Progress-ID' in request.GET:
        progress_id = request.GET['X-Progress-ID']
    elif 'X-Progress-ID' in request.META:
        progress_id = request.META['X-Progress-ID']
    if progress_id:
        cache_key = "%s_%s" % (request.META['REMOTE_ADDR'], progress_id)
        data = cache.get(cache_key)
        return HttpResponse(simplejson.dumps(data))
    else:
        return HttpResponseServerError('Server Error: You must provide X-Progress-ID header or query param.')