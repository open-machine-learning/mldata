from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from utils import slugify
from tagging.fields import TagField
from settings import DATAPATH, SPLITPATH

TYPE = {
    'data': 0,
    'task': 1,
    'solution': 2,
}



class Slug(models.Model):
    text = models.CharField(max_length=32, unique=True)

    def __unicode__(self):
        return unicode(self.text)


class License(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.CharField(max_length=255)

    def __unicode__(self):
        return unicode(self.name)

# doesn't work
#class DataLicense(License):
#    pass

class DataLicense(models.Model):
    name = models.CharField(max_length=255, unique=True)
    url = models.CharField(max_length=255)

    def __unicode__(self):
        return unicode(self.name)




class Repository(models.Model):
    pub_date = models.DateTimeField()
    version = models.IntegerField()
    name = models.CharField(max_length=32)
    slug = models.ForeignKey(Slug)
    summary = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    urls = models.CharField(max_length=255, blank=True)
    publications = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    user = models.ForeignKey(User)
    average_rating = models.FloatField(editable=False, default=-1)
    average_interesting_rating = models.FloatField(editable=False, default=-1)
    average_documentation_rating = models.FloatField(editable=False, default=-1)
    total_number_of_votes = models.IntegerField(editable=False, default=0)
    tags = TagField()


    class Meta:
        ordering = ('-pub_date',)
        get_latest_by = 'pub_date'


    def __unicode__(self):
        return unicode(self.name)


    def save(self):
        if not self.slug_id:
            self.slug_id = self.get_slug_id()
        super(Repository, self).save()


    def delete(self):
        try:
            Slug.objects.get(pk=self.slug.id).delete()
        except Slug.DoesNotExist:
            pass
        # calling delete in parent not necessary
        #super(Repository, self).delete()


    def get_slug_id(self):
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


    @classmethod
    def edit(klass, repository):
        try:
            cv = klass.objects.get(slug=repository.slug)
        except klass.DoesNotExist:
            cv = klass()
            # can't put foreign key id into constructor
            cv.slug = repository.slug
            cv.type = TYPE[repository.__class__.__name__.lower()]

        cv.repository = repository
        cv.save()


    def __unicode__(self):
        return unicode('%s %s' % (self.repository.version, self.slug.text))


class Data(Repository):
    source = models.CharField(max_length=255, blank=True)
    format = models.CharField(max_length=16) # CSV, ARFF, netCDF, HDF5, ODBC
    measurement_details = models.TextField(blank=True)
    usage_scenario = models.TextField(blank=True)
    file = models.FileField(upload_to=DATAPATH)
    license = models.ForeignKey(DataLicense)
    # is_approved is necessary for 2-step creation, don't want to call review
    # ever again once the item is approved - review can remove permanently via
    # 'Back' button!
    is_approved = models.BooleanField(default=False)

    def get_absolute_url(self, use_slug=False):
        if use_slug:
            args=[self.slug.text]
        else:
            args=[self.id]
        return reverse('repository.views.data_view', args=args)


    def get_filename(self):
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        return self.slug.text + '.' + self.format



class Task(Repository):
    input = models.CharField(max_length=255)
    output = models.CharField(max_length=255)
    performance_measure = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    data = models.ManyToManyField(Data)
    splits = models.FileField(upload_to=SPLITPATH)
    license = models.ForeignKey(License)

    def get_absolute_url(self):
        return reverse('repository.views.task_view', args=[self.slug.text])


class Solution(Repository):
    feature_processing = models.CharField(max_length=255)
    parameters = models.CharField(max_length=255)
    os = models.CharField(max_length=255)
    code = models.TextField()
    score = models.FileField(upload_to='repository/scores')
    task = models.ForeignKey(Task)
    license = models.ForeignKey(License)


class Rating(models.Model):
    """Rating for a repository item

    Each user can rate a repository item only once, but she might change
    her rating later on.
    It acts as a base class for more specific Rating classes.
    """
    user = models.ForeignKey(User)
    interesting = models.IntegerField(default=0)
    documentation = models.IntegerField(default=0)

    def update_rating(self, i, d):
        self.interesting = i
        self.documentation = d
        self.save()

        repo = self.repository
        ratings = self.__class__.objects.filter(repository=repo)
        l = float(len(ratings))
        i=d=0
        for r in ratings:
            i+= r.interesting
            d+= r.documentation

        repo.average_rating = (i+d)/(3.0*l)
        repo.average_interesting_rating = float(i)/l
        repo.average_documentation_rating = float(d)/l
        repo.total_number_of_votes = l
        repo.save()

    def __unicode__(self):
        try:
            return unicode("%s %s %s" % (self.user.username, _('on'), self.repository.name))
        except AttributeError:
            return unicode("%s %s %s" % (self.user.username, _('on'), self.id))

class DataRating(Rating):
    repository = models.ForeignKey(Data)
class TaskRating(Rating):
    repository = models.ForeignKey(Task)
class SolutionRating(Rating):
    repository = models.ForeignKey(Solution)
