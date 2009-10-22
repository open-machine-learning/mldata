from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from utils import slugify
from tagging.fields import TagField

TYPE = {
    'data': 0,
    'task': 1,
    'solution': 2,
}


class Slug(models.Model):
    text = models.CharField(max_length=32, unique=True)

    def __unicode__(self):
        return unicode(self.text)


class Repository(models.Model):
    pub_date = models.DateTimeField()
    version = models.IntegerField()
    name = models.CharField(max_length=32)
    slug = models.ForeignKey(Slug)
    summary = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    urls = models.CharField(max_length=255, blank=True)
    publications = models.CharField(max_length=255, blank=True)
    license = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    author = models.ForeignKey(User)

    class Meta:
        ordering = ('-pub_date',)
        get_latest_by = 'pub_date'

    def __unicode__(self):
        return unicode(self.name)

    def save(self, type):
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'
        current = CurrentVersion.objects.filter(slug=self.slug_id)
        if current: # only update current version if this is public
            if not self.is_public:
                super(Repository, self).save()
                return
            current = current[0]
        else: # new item, create current version even if not public
            current = CurrentVersion()
            # can't put foreign key id into constructor
            current.slug_id = self.slug_id
        current.type = type
        # saves as close together as possible
        super(Repository, self).save()
        current.repository_id = self.id
        current.save()

    def get_slug_id(self, create=False):
        if not self.name:
            raise AttributeError, 'Attribute name is not set!'
        slug = Slug(text=slugify(self.name))
        slug.save()
        return slug.id

    def get_next_version(self, type):
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'
        obj = eval(self.__class__.__name__).objects.filter(slug=self.slug_id).order_by('-version')
        return obj[0].version + 1


class CurrentVersion(models.Model):
    slug = models.ForeignKey(Slug)
    repository = models.ForeignKey(Repository)
    type = models.IntegerField() # crutch for lookups of data/task/solution

    def __unicode__(self):
        return unicode('%s %s' % (self.repository.version, self.slug.text))


class Data(Repository):
    source = models.CharField(max_length=255, blank=True)
    format = models.CharField(max_length=16) # CSV, ARFF, netCDF, HDF5, ODBC
    measurement_details = models.TextField(blank=True)
    usage_scenario = models.TextField(blank=True)
    file = models.FileField(upload_to='repository/data')
    tags = TagField()

    def get_absolute_url(self, use_slug=True):
        if use_slug:
            args=[self.slug.text]
        else:
            args=[self.id]
        return reverse('repository.views.data_view', args=args)

    def get_filename(self):
        if not self.slug_id:
            self.make_slug()
        return '%s.%s' % (self.slug.text, self.format)


class Task(Repository):
    format_input = models.CharField(max_length=255)
    format_output = models.CharField(max_length=255)
    performance_measure = models.CharField(max_length=255)
    data = models.ManyToManyField(Data)

    def get_absolute_url(self):
        return reverse('repository.views.task_view', args=[self.slug.text])


class Solution(Repository):
    feature_processing = models.CharField(max_length=255)
    parameters = models.CharField(max_length=255)
    os = models.CharField(max_length=255)
    code = models.TextField()
    score = models.FileField(upload_to='repository/scores')
    task = models.ForeignKey(Task)


class Split(models.Model):
    data = models.ForeignKey(Data)
    task = models.ForeignKey(Task)
    splits = models.FileField(upload_to='repository/splits')

    def get_absolute_url(self):
        return self.splits.url

