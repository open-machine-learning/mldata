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
    average_rating = models.FloatField(editable=False, default=-1)
    average_features_rating = models.FloatField(editable=False, default=-1)
    average_usability_rating = models.FloatField(editable=False, default=-1)
    average_documentation_rating = models.FloatField(editable=False, default=-1)
    total_number_of_votes = models.IntegerField(editable=False, default=0)


    class Meta:
        ordering = ('-pub_date',)
        get_latest_by = 'pub_date'

    def __unicode__(self):
        return unicode(self.name)

    def save(self):
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
        current.type = TYPE[self.__class__.__name__.lower()]
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

    def get_next_version(self):
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'
        obj = self.__class__.objects.filter(slug=self.slug_id).order_by('-version')
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

    def get_absolute_url(self, use_slug=False):
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


class Rating(models.Model):
    """Rating for a repository

    Each user can rate a repository item only once (but she might change
    her rating?)"""
    user = models.ForeignKey(User)
    features = models.IntegerField(default=0)
    usability = models.IntegerField(default=0)
    documentation = models.IntegerField(default=0)

    def update_rating(self, f, u, d):
        self.features = f
        self.usability = u
        self.documentation = d
        self.save()

        repo = self.repository
        ratings = self.__class__.objects.filter(repository=repo)
        l = float(len(ratings))
        f=u=d=0
        for r in ratings:
            f+= r.features
            u+= r.usability
            d+= r.documentation

        repo.average_rating = (f+u+d)/(3.0*l)
        repo.average_features_rating = float(f)/l
        repo.average_usability_rating = float(u)/l
        repo.average_documentation_rating = float(d)/l
        repo.total_number_of_votes = l
        repo.save()


class DataRating(Rating):
    repository = models.ForeignKey(Data)
class TaskRating(Rating):
    repository = models.ForeignKey(Task)
class SolutionRating(Rating):
    repository = models.ForeignKey(Solution)
