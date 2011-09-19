"""
Module resposible for communication with datacite.org. Retrives DOI
identificator and posts dataset's description.

Code based on datacite documentation v2 https://mds.datacite.org/static/apidoc/
"""
import httplib2, sys, base64, codecs
from django.conf import settings

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
    body_unicode = u"doi=%s\nurl=%s\n" % (doi,location)
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
