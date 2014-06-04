from django.db import models
from repository.models.data import Data
from datacite import get_doi, metadata_xml_string, metadata_post, doi_post

class DOIManager(models.Manager):
    """Manager which simplifies DOI creation
    
    In order to create DOI for dataset it is sufficient to call:
    DOI.objects.create_for_data(data)
    
    where data is Data entity (repository.models.data.Data)
    """
    
    def create_for_data(self, data):
        """Cover whole DOI generation and submition 
        for given data object
    
        @param data: object to submit
        @type doi: repository.models.data.Data
        """
        doi = get_doi(data)
        location = data.get_absolute_slugurl()
        
        doi_post(doi,location)
        doi.save()
        metadata_post(metadata_xml_string(data))
        
        return doi

class DOI(models.Model):
    """Very simple model for storing datacite identifier

    Designed so that identifier is stored in separated table.
    This simplifies the design but requires additional SQL select
    while accessing "dataset.doi" directly form data entity.
    That is why for views where DOI is used, adding "select_related('doi')"
    to the query is recommended.

    @cvar data: The dataset to which the doi is attached
    @type data: repository.models.data.Data
    @cvar slug: short identified (the actual DOI)
    @type slug: string
    """
    data = models.OneToOneField(Data)
    slug = models.CharField(max_length=255, unique=True)
    
    objects = DOIManager()
    
    def __str__(self):
        return self.slug
    
    def __unicode__(self):
        return self.slug