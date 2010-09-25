from django.db import models
from django.core.urlresolvers import reverse

from repository.models import Repository
from repository.models import Rating
from repository.models import FixedLicense

from tagging.fields import TagField
from task import Task
from challenge import Challenge

from utils import slugify

from settings import SCOREPATH

# Create your models here.
class Solution(Repository):
    """Repository item Solution.

    @cvar feature_processing: item's feature processing
    @type feature_processing: string / models.TextField
    @cvar parameters: item's parameters
    @type parameters: string / models.CharField
    @cvar os: operating system used
    @type os: string / models.CharField
    @cvar code: computer source code to provide solution
    @type code: string / models.TextField
    @cvar software_packages: software packages needed for evaluation
    @type software_packages: string / models.TextField
    @cvar license: item's license
    @type license: FixedLicense
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    feature_processing = models.TextField(blank=True)
    parameters = models.CharField(max_length=255, blank=True)
    os = models.CharField(max_length=255, blank=True)
    code = models.TextField(blank=True)
    software_packages = models.TextField(blank=True)
    license = models.ForeignKey(FixedLicense, editable=False)
    tags = TagField() # tagging doesn't work anymore if put into base class

    class Meta:
        app_label = 'repository'

    def get_completeness_properties(self):
        return ['tags', 'description', 'summary', 'urls', 'publications',
            'feature_processing', 'parameters', 'os', 'code',
            'software_packages']

    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        @return: an absolute URL or None
        @rtype: string
        """
        view = 'repository.views.solution.view_slug'
        return reverse(view, args=[self.slug.text])

class SolutionRating(Rating):
    """Rating for a Solution item."""
    repository = models.ForeignKey(Solution)

    class Meta:
        app_label = 'repository'

class Result(Repository):
    """Repository item Result.

    @cvar score: score file
    @type score: models.FileField
	"""

    task = models.ForeignKey(Task)
    solution = models.ForeignKey(Solution)
    challenge = models.ForeignKey(Challenge, blank=True, null=True)
    output_file = models.FileField(upload_to=SCOREPATH)
    aggregation_score = models.FloatField(default=-1)
    complex_result= models.TextField(blank=True)
    complex_result_type = models.CharField(max_length=255, blank=True)

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

    class Meta:
        app_label = 'repository'

class ResultRating(Rating):
    """Rating for a Solution item."""
    repository = models.ForeignKey(Result)

    class Meta:
        app_label = 'repository'
