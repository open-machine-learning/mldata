from django.db import models
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.core.mail import mail_admins
from django.contrib import admin
import repository
from repository.models import License, Repository

from settings import DATAPATH, MEDIA_ROOT

from repository.models import Rating

from tagging.fields import TagField
from tagging.models import Tag
from tagging.models import TaggedItem
from tagging.utils import calculate_cloud

from utils import slugify

import ml2h5
import ml2h5.data
import os

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
    @cvar dependencies: dataset dependencies (one way relation)
    @type dependencies: Data / models.ManyToManyField
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
    #has_missing_values = models.BooleanField(blank=True, default=False)
    tags = TagField() # tagging doesn't work anymore if put into base class
    dependencies = models.ManyToManyField('Data', blank=True, related_name="base_for")

    extract = models.TextField(blank=True)
    attribute_types = models.TextField(blank=True)

    class Meta:
        app_label = 'repository'
        
    def conversion_failed(self):
        if self.format != 'hd5':
            return True
        return False

    @classmethod
    def get_public_active_objects(cls):
        """Get the currently active objects.

        Currently, this includes:

        * not deleted
        * approved
        * current
        * public
        """
        return cls.objects.filter(is_deleted=False, is_approved=True, is_current=True, is_public=True)

    def get_filename(self):
        """Construct filename for Data file.

        @return: filename for Data file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        return self.slug.text + '.' + self.format

    def get_data_filename(self):
        return os.path.join(MEDIA_ROOT, self.file.name)

    def approve(self, fname_orig, convdata):
        """Approve Data item.

        @param fname_orig: original name of Data file
        @type fname_orig: string
        @param convdata: conversion-relevant data
        @type convdata: dict of strings with keys seperator, convert, format + attribute_names_first
        @raise: ml2h5.converter.ConversionError if conversion failed
        @raise: ml2h5.converter.ConversionUnsupported if an unsupported conversion was tried
        """
        self.is_approved = True
        self.format = convdata['format']
        fname_h5 = ml2h5.fileformat.get_filename(fname_orig)

        if 'convert' in convdata and convdata['convert'] and self.format in ml2h5.converter.TO_H5:
            if 'attribute_names_first' in convdata and convdata['attribute_names_first']:
                anf = True
            else:
                anf = False

            #verify = True
            #if convdata['format'] == 'uci': verify = False
            verify = False

            try:
                seperator=convdata['seperator']
                if seperator and not len(seperator):
                    seperator=None
                c = ml2h5.converter.Converter(
                                              fname_orig, fname_h5, format_in=self.format,
                                              seperator=seperator,
                                              attribute_names_first=anf
                                              )
                c.run(verify=verify)
            except ml2h5.converter.ConversionError, error:
                # save it anyway but keep private
                self.is_public = False
                self.save()
                raise ml2h5.converter.ConversionError(error.value)

        if os.path.isfile(fname_h5):
            (self.num_instances, self.num_attributes) = ml2h5.data.get_num_instattr(fname_h5)
            # keep original file for the time being
            #os.remove(fname_orig)
            self.file.name = os.path.join(DATAPATH, fname_h5.split(os.path.sep)[-1])

        self.save()

    def dependent_entries_exist(self):
        """Check whether there exists an object which depends on self.

        For Data objects, checks whether there exists a Task object,
        """
        if repository.models.Task.objects.filter(data__slug=self.slug).count() > 0:
            return True
        return False

    def attach_file(self, file_object):
        self.file = file_object

    def get_public_qs(self, user=None, queryset=None):
        qs=super(Data, self).get_public_qs(user)

        if queryset:
            qs=qs & Q(is_approved=True)

        return qs

    def get_related_tasks(self, user=None):
        from repository.models.task import Task
        return Task.objects.filter(Q(data=self.pk) & self.get_public_qs(self))

    def get_related_methods(self):
        from repository.models.method import Result
        return Result.objects.filter(task__data=self.pk)

    def get_related_challenges(self, user=None):
        from repository.models.challenge import Challenge
        return Challenge.objects.filter(Q(task__data=self.pk) & self.get_public_qs(self))

    def get_completeness_properties(self):
        return ['tags', 'description', 'license', 'summary', 'urls',
            'publications', 'source', 'measurement_details', 'usage_scenario']

    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        @return: an absolute URL or None
        @rtype: string
        """
        view = 'repository.views.data.view_slug'
        return reverse(view, args=[self.slug.text])

    def get_extract(self):
        if not self.extract:
            fname_h5 = self.get_data_filename()
            try:
                self.extract = ml2h5.data.get_extract(fname_h5)
                extr = self.extract
                self.save(silent_update=True)
            except Exception, e: # catch exceptions in general, but notify admins
                subject = 'Failed data extract of %s' % (fname_h5)
                body = "Hi Admin!" + "\n\n" + subject + ":\n\n" + str(e)
                mail_admins(subject, body)
        else:
            try:
                extr = eval(self.extract)
            except Exception, e:
                extr = {}
        return extr

    def has_h5(self):
        return self.get_data_filename().endswith('.h5')

    def check_is_approved(self):
        return self.is_approved

    def get_attribute_types(self):
        if not self.attribute_types:
            self.attribute_types = ml2h5.data.get_attribute_types(self.get_data_filename())
            self.save(silent_update=True)
        attr = self.attribute_types
        return attr

    def can_convert_to_arff(self):
        return ml2h5.fileformat.can_convert_h5_to('arff', self.get_data_filename())
    def can_convert_to_libsvm(self):
        return ml2h5.fileformat.can_convert_h5_to('libsvm', self.get_data_filename())
    def can_convert_to_octave(self):
        return ml2h5.fileformat.can_convert_h5_to('octave', self.get_data_filename())
    def can_convert_to_rdata(self):
        return ml2h5.fileformat.can_convert_h5_to('rdata', self.get_data_filename())
    def can_convert_to_matlab(self):
        return ml2h5.fileformat.can_convert_h5_to('matlab', self.get_data_filename())
    def can_convert_to_csv(self):
        return ml2h5.fileformat.can_convert_h5_to('csv', self.get_data_filename())

class DataRating(Rating):
    """Rating for a Data item."""
    repository = models.ForeignKey(Data)

    class Meta:
        app_label = 'repository'


class DataAdmin(admin.ModelAdmin):
    actions = ['rename_file']

    def rename_file(self, request, queryset):
        """Move the file"""
        old_name = request.file.name
        new_name = "dummy"
        #file_move_safe(old_name, new_name, allow_overwrite=False)
        self.message_user(request, "Moved file from %s to %s" % (old_name, new_name))
    rename_file.short_description = "Move the data file (one item only please!)"
admin.site.register(DataAdmin)
