"""
View for datacite application. Display metadata about dataset
in the xml format.
"""
from django.shortcuts import render_to_response
from django.template import RequestContext
from repository.models.data import Data

def metadata_xml(request, doi):
    """
    Show the metadata of the dataset under given DOI.
    
    **Required arguments**
    
    ``doi``
        DOI string in format prefix:slugid:version
    
    **Context:**
    
    ``data``
        The dataset in proper version.
    
    **Template:**
    
    datacite/metadata.xml - in current version xml is generated
    by filling the template.
    
    """
    context = RequestContext(request)
    prefix, id, version = doi.split(':')
    data = Data.objects.get(slug__id=id,version=version)
    data.doi = doi
    
    return render_to_response('datacite/metadata.xml',
                              {'data': data},
                              context_instance=context)
