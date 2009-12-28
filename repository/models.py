"""
Model classes for app Repository

@var TYPE: available item types - mainly used as a crutch
@type TYPE: dict
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from utils import slugify
from tagging.fields import TagField
from settings import DATAPATH, SPLITPATH, SCOREPATH

TYPE = {
    'Data': 0,
    'Task': 1,
    'Solution': 2,
}



class Slug(models.Model):
    """Slug - URL-compatible item name.

    @cvar text: URL-compatible item name
    @type text: string / models.CharField
    """
    text = models.CharField(max_length=32, unique=True)

    def __unicode__(self):
        return unicode(self.text)


class License(models.Model):
    """License to be used by Task or Solution items.

    @cvar name: name of the license
    @type name: string / models.CharField
    @cvar url: url of the license
    @type url: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)
    url = models.CharField(max_length=255)

    def __unicode__(self):
        return unicode(self.name)



class DataLicense(models.Model):
    """License to be used by Data items.

    For some reason, it didn't work when it just inherited from License, so
    the code needs to be duplicated.

    @cvar name: name of the license
    @type name: string / models.CharField
    @cvar url: url of the license
    @type url: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)
    url = models.CharField(max_length=255)

    def __unicode__(self):
        return unicode(self.name)



class TaskType(models.Model):
    """Type of a Task.

    @cvar name: name of the license
    @type name: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)

    def __unicode__(self):
        return unicode(self.name)



class Repository(models.Model):
    """Base class for Repository items: Data, Task, Solution

    @cvar pub_date: publication date (item creation date)
    @type pub_date: models.DateTimeField
    @cvar version: version number to flip between different incarnations of the item
    @type version: integer / models.IntegerField
    @cvar name: item's name
    @type name: string / models.CharField
    @cvar slug: item's slug
    @type slug: string / Slug
    @cvar summary: item's summary
    @type summary: string / models.CharField
    @cvar description: item's description
    @type description: string / models.TextField
    @cvar urls: URLs linking to more information about item
    @type urls: string / models.CharField
    @cvar publications: publications where item is mentioned or used
    @type publications: string / models.CharField
    @cvar is_public: if item is public
    @type is_public: boolean / models.BooleanField
    @cvar is_deleted: if item is deleted
    @type is_deleted: boolean / models.BooleanField
    @cvar user: user who created the item
    @type user: Django User
    @cvar average_rating: item's average overal rating
    @type average_rating: float / models.FloatField
    @cvar average_interesting_rating: item's average interesting rating
    @type average_interesting_rating: float / models.FloatField
    @cvar average_documentation_rating: item's average documentation rating
    @type average_documentation_rating: float / models.FloatField
    @cvar total_number_of_votes: item's total number of votes
    @type total_number_of_votes: integer / models.IntegerField
    """
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


    class Meta:
        """Inner meta class to specify options.

        @cvar ordering: default ordering of items in queries
        @type ordering: list
        @cvar get_latest_by: latestness will be determined by this field
        @type get_latest_by: string
        """
        ordering = ('-pub_date',)
        get_latest_by = 'pub_date'


    def __unicode__(self):
        return unicode(self.name)


    def save(self):
        """Save item.

        Creates a slug if necessary.
        """
        if not self.slug_id:
            self.slug_id = self.get_slug_id()
        super(Repository, self).save()


    def delete(self):
        """Delete item.

        Delete the corresponding slug.
        """
        try:
            Slug.objects.get(pk=self.slug.id).delete()
        except Slug.DoesNotExist:
            pass
        # calling delete in parent not necessary
        #super(Repository, self).delete()


    def get_slug_id(self):
        """Get the id of the slug generated for the item's name.

        @return: slug's id
        @rtype: integer
        @raise AttributeError: if item's name is not set
        """
        if not self.name:
            raise AttributeError, 'Attribute name is not set!'
        slug = Slug(text=slugify(self.name))
        slug.save()
        return slug.id


    def get_next_version(self):
        """Get next available version for this item.

        @return: next available version
        @rtype: integer
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'
        objects = self.__class__.objects.filter(
            slug=self.slug_id, is_deleted=False
        ).order_by('-version')
        return objects[0].version + 1


    def get_absolute_url(self):
        """Get absolute URL for this item, using its id.

        @return: an absolute URL
        @rtype: string
        """
        view = 'repository.views.' + self.__class__.__name__.lower() + '_view'
        return reverse(view, args=[self.id])


    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        @return: an absolute URL
        @rtype: string
        """
        view = 'repository.views.' + self.__class__.__name__.lower() + '_view'
        return reverse(view, args=[self.slug.text])



class CurrentVersion(models.Model):
    """Lookup model to find current version of an item quickly.

    @cvar slug: slug of the item
    @type slug: Slug
    @cvar repository: related item
    @type repository: Repository (indirectly: Data, Task or Solution)
    @cvar type: crutch for lookups in Data, Task or Solution
    @type type: integer / models.IntegerField
    """
    slug = models.ForeignKey(Slug)
    repository = models.ForeignKey(Repository)
    type = models.IntegerField() # 


    @classmethod
    def set(klass, repository):
        """Class method to set the current item.

        @param klass: item's class
        @type klass: Data, Task or Solution
        @param repository: item
        @type repository: Repository
        """
        try:
            cv = klass.objects.get(slug=repository.slug)
        except klass.DoesNotExist:
            cv = klass()
            # can't put foreign key id into constructor
            cv.slug = repository.slug
            cv.type = TYPE[repository.__class__.__name__]

        cv.repository = repository
        cv.save()


    def __unicode__(self):
        return unicode('%s %s' % (self.repository.version, self.slug.text))


class Data(Repository):
    """Repository item Data.

    @cvar source: source of the data
    @type source: string / models.CharField
    @cvar format: data format, e.g. CSV, ARFF, netCDF, HDF5, ODBC
    @type format: string / models.CharField
    @cvar measurement_details: item's measurement details
    @type measurement_details: string / models.TextField
    @cvar usage_scenario: item's usage scenario
    @type usage_scenario: string / models.TextField
    @cvar file: data file
    @type file: models.FileField
    @cvar license: license of Data item
    @type license: DataLicense
    @cvar is_approved: is_approved is necessary for 2-step creation, don't want to call review ever again once the item is approved - review can remove permanently via 'Back' button!
    @type is_approved: boolean / models.BooleanField
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    source = models.CharField(max_length=255, blank=True)
    format = models.CharField(max_length=16)
    measurement_details = models.TextField(blank=True)
    usage_scenario = models.TextField(blank=True)
    file = models.FileField(upload_to=DATAPATH)
    license = models.ForeignKey(DataLicense)
    is_approved = models.BooleanField(default=False)
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



class Task(Repository):
    """Repository item Task.

    @cvar input: item's input format
    @type input: string / models.TextField
    @cvar output: item's output format
    @type output: string / models.TextField
    @cvar performance_measure: item's performance measure
    @type performance_measure: string / models.TextField
    @cvar type: item's type, e.g. Regression, Classification
    @type type: TaskType
    @cvar data: related Data item(s)
    @type data: Data / models.ManyToManyField
    @cvar splits: item's data splits
    @type splits: models.FileField
    @cvar license: item's license
    @type license: License
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    input = models.TextField(blank=True)
    output = models.TextField(blank=True)
    performance_measure = models.TextField(blank=True)
    type = models.ForeignKey(TaskType)
    data = models.ManyToManyField(Data, blank=True)
    splits = models.FileField(upload_to=SPLITPATH)
    license = models.ForeignKey(License)
    tags = TagField() # tagging doesn't work anymore if put into base class


    def get_splitname(self):
        """Construct filename for splits file.

        @return: filename for splits file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        suffix = self.splits.name.split('.')[-1]

        return self.slug.text + '.' + suffix



class Solution(Repository):
    """Repository item Solution.

    @cvar feature_processing: item's feature processing
    @type feature_processing: string / models.CharField
    @cvar parameters: item's parameters
    @type parameters: string / models.CharField
    @cvar os: operating system used
    @type os: string / models.CharField
    @cvar code: computer source code to provide solution
    @type code: string / models.TextField
    @cvar score: score file
    @type score: models.FileField
    @cvar task: related Task
    @type task: Task
    @cvar license: item's license
    @type license: License
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    feature_processing = models.CharField(max_length=255, blank=True)
    parameters = models.CharField(max_length=255, blank=True)
    os = models.CharField(max_length=255, blank=True)
    code = models.TextField(blank=True)
    score = models.FileField(upload_to=SCOREPATH)
    task = models.ForeignKey(Task)
    license = models.ForeignKey(License)
    tags = TagField() # tagging doesn't work anymore if put into base class


    def get_scorename(self):
        """Construct filename for score file.

        @return: filename for score file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        suffix = self.score.name.split('.')[-1]

        return self.slug.text + '.' + suffix



class Rating(models.Model):
    """Rating for a Repository item

    Each user can rate a Repository item only once, but she might change
    her rating later on.
    It acts as a base class for more specific Rating classes.

    @cvar user: rating user
    @type user: Django User
    @cvar interesting: how interesting the item is
    @type interesting: integer / models.IntegerField
    @cvar documentation: how well the item is documented
    @type documentation: integer / models.IntegerField
    """
    user = models.ForeignKey(User)
    interesting = models.IntegerField(default=0)
    documentation = models.IntegerField(default=0)

    def update_rating(self, i, d):
        """Update rating for an item.

        @param i: interesting value
        @type i: integer
        @param d: documentation value
        @type d: integer
        """
        self.interesting = i
        self.documentation = d
        self.save()

        repo = self.repository
        ratings = self.__class__.objects.filter(repository=repo)
        l = float(len(ratings))
        i = d = 0
        for r in ratings:
            i += r.interesting
            d += r.documentation

        num_scores = 2.0
        repo.average_rating = (i + d) / (num_scores * l)
        repo.average_interesting_rating = float(i) / l
        repo.average_documentation_rating = float(d) / l
        repo.total_number_of_votes = l
        repo.save()

    def __unicode__(self):
        try:
            return unicode("%s %s %s" % (self.user.username, _('on'), self.repository.name))
        except AttributeError:
            return unicode("%s %s %s" % (self.user.username, _('on'), self.id))

class DataRating(Rating):
    """Rating for a Data item."""
    repository = models.ForeignKey(Data)
class TaskRating(Rating):
    """Rating for a Task item."""
    repository = models.ForeignKey(Task)
class SolutionRating(Rating):
    """Rating for a Solution item."""
    repository = models.ForeignKey(Solution)
