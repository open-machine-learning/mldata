from django.db import models
from django.db.models import Q
from repository.models import Repository
from repository.models import License

from settings import DATAPATH

from repository.models import Rating

from tagging.fields import TagField
from tagging.models import Tag
from tagging.models import TaggedItem
from tagging.utils import calculate_cloud

from utils import slugify

class Data(Repository):
    """Repository item Data.

    @cvar source: source of the data
    @type source: string / models.CharField
    @cvar format: data format of original file, e.g. CSV, ARFF, HDF5
    @type format: string / models.CharField
    @cvar measurement_details: item's measurement details
    @type measurement_details: string / models.TextField
    @cvar usage_scenario: item's usage scenario
    @type usage_scenario: string / models.TextField
    @cvar file: data file
    @type file: models.FileField
    @cvar license: license of Data item
    @type license: License
    @cvar is_approved: is_approved is necessary for 2-step creation, don't want to call review ever again once the item is approved - review can remove permanently via 'Back' button!
    @type is_approved: boolean / models.BooleanField
    @cvar num_instances: number of instances in the Data file
    @type num_instances: integer / models.IntegerField
    @cvar num_attributes: number of attributes in the Data file
    @type num_attributes: integer / models.IntegerField
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    source = models.TextField(blank=True)
    format = models.CharField(max_length=16)
    measurement_details = models.TextField(blank=True)
    usage_scenario = models.TextField(blank=True)
    file = models.FileField(upload_to=DATAPATH)
    license = models.ForeignKey(License)
    is_approved = models.BooleanField(default=False)
    num_instances = models.IntegerField(blank=True, default=-1)
    num_attributes = models.IntegerField(blank=True, default=-1)
    tags = TagField() # tagging doesn't work anymore if put into base class


    def get_filename(self):
        """Construct filename for Data file.

        @return: filename for Data file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        return self.slug.text + '.' + self.format

    def get_media_file_name(self):
        return os.path.join(MEDIA_ROOT, self.file.name)

    def approve(self, fname_orig, convdata):
        """Approve Data item.

        @param fname_orig: original name of Data file
        @type fname_orig: string
        @param convdata: conversion-relevant data
        @type convdata: dict of strings with keys seperator, convert, format + attribute_names_first
        @raise: ml2h5.converter.ConversionError if conversion failed
        """
        self.is_approved = True
        self.format = convdata['format']
        fname_h5 = ml2h5.fileformat.get_filename(fname_orig)

        if 'convert' in convdata and convdata['convert'] and self.format != 'h5':
            if 'attribute_names_first' in convdata and convdata['attribute_names_first']:
                anf = True
            else:
                anf = False

            verify = True
            if convdata['format'] == 'uci': verify = False

            try:
                c = ml2h5.converter.Converter(
                                              fname_orig, fname_h5, format_in=self.format,
                                              seperator=convdata['seperator'],
                                              attribute_names_first=anf
                                              )
                c.run(verify=verify)
            except ml2h5.converter.ConversionError, error:
                if self.tags:
                    self.tags += ', conversion_failed'
                else:
                    self.tags = 'conversion_failed'

                self.save()
                raise ml2h5.converter.ConversionError(error.value)

        if os.path.isfile(fname_h5):
            (self.num_instances, self.num_attributes) = ml2h5.data.get_num_instattr(fname_h5)
            # keep original file for the time being
            #os.remove(fname_orig)
            # for some reason, FileField saves file.name as DATAPATH/<basename>
            self.file.name = os.path.join(DATAPATH, fname_h5.split(os.path.sep)[-1])

        self.save()

    def attach_file(self, file_object):
        self.file = file_object

    @classmethod
    def get_query(cls, qs):
        return qs & Q(is_approved=True)

class DataRating(Rating):
    """Rating for a Data item."""
    repository = models.ForeignKey(Data)
