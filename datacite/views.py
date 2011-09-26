"""
View for datacite application. Display metadata about dataset
in the xml format.
"""
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.template import RequestContext, loader
from django.http import HttpResponse, HttpResponseRedirect
from repository.models.data import Data
from datacite import metadata_xml_string
from datacite.models import DOI

def metadata_xml(request, doi):
    """
        View displays datacite information
        for given DOI.
    """
    data = Data.objects.get(doi__slug=doi)
    return HttpResponse(metadata_xml_string(data))

def datacite_post(request, slug):
    """
        View posts new data to datacite and requests for a DOI
    """
    data = Data.get_object(slug)
    if request.user == data.user:
        DOI.objects.create_for_data(data)
    return HttpResponseRedirect(reverse('data_view_slug', args=[slug,]))
