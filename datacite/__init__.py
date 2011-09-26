"""
Module resposible for communication with datacite.org. Retrives DOI
identificator and posts dataset's description.

Code based on datacite documentation v2 https://mds.datacite.org/static/apidoc/
"""
import httplib2, sys, base64, codecs
from django.conf import settings
from django.template import Context, loader

class DataciteAPIException(Exception):
    """Handles all exceptions which comes from API
    at once. Each API command results in status code and message
    so the exception is initialized by those two values.
    """
    def __init__(self, value, msg):
        self.value = value
        self.msg = msg
    def __str__(self):
        return ("%s: %s") % (repr(self.value),self.msg)

def datacite_command(req,method,body_unicode = ''):
    """Call datacite API command

    @param req: requested command
    @type req: string
    @param method: http method ('GET' or 'POST')
    @type location: string
    @return: response type and message
    @rtype: tuple of int and string
    """
    h = httplib2.Http()
    auth_string = base64.encodestring(settings.DATACITE_USERNAME + ':' + settings.DATACITE_PASSWORD)
    
    response, content = h.request(settings.DATACITE_API_URL + req,
                                  method,
                                  body = body_unicode.encode('utf-8'),
                                  headers={'Content-Type':'text/plain;charset=UTF-8',
                                           'Authorization':'Basic ' + auth_string})
    
    if (response.status > 201):
        raise DataciteAPIException(response.status, content.decode('utf-8'))
    return response.status, content.decode('utf-8')

def doi_post(doi, location): 
    """Request new doi for given location

    @param doi: requested doi
    @type doi: string
    @param location: URI of the dataset
    @type location: string
    @return: response type and message
    @rtype: tuple of int and string
    """
    body_unicode = u"doi=%s\nurl=http://%s%s\n" % (doi,settings.DATACITE_DOMAIN,location)
    return datacite_command('/doi','POST',body_unicode)

def metadata_get(doi): 
    """Get location for given doi

    @param doi: DOI of the dataset to check
    @type doi: string
    @return: response type and message
    @rtype: tuple of int and string
    """
    return datacite_command('/doi/' + doi,'GET')

def metadata_post(metadata): 
    """Update metadata for given location

    @param metadata: metadata in XML format
    @type metadata: string
    @return: response type and message
    @rtype: tuple of int and string
    """
    return datacite_command('/metadata','POST',metadata)

def metadata_get(doi):
    """Get metadata for given doi

    @param doi: DOI of the dataset to check
    @type doi: string
    @return: response type and message
    @rtype: tuple of int and string
    """
    return datacite_command('/metadata/' + doi,'GET')

def get_doi(data):
    """
        Generate doi for a given dataset
    """
    from datacite.models import DOI
    doi, c = DOI.objects.get_or_create(slug=settings.DATACITE_FORMAT % {'slug': data.slug.__str__().upper(),
                                       'version': data.version},
        data=data)
    return doi

def metadata_xml_string(data):
    """
    Show the metadata of the dataset under given DOI.
    
    **Required arguments**
    
    ``data``
        data object
    
    **Context:**
    
    ``data``
        data object
    
    **Template:**
    
    datacite/metadata.xml - in current version xml is generated
    by filling the template.
    
    """
    context = Context()
    data.doi = get_doi(data)
    
    t = loader.get_template('datacite/metadata.xml')
    c = Context({'data': data})
    return t.render(c)

