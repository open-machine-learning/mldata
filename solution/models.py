from django.db import models

from repository.models import Repository
from repository.models import Rating
from repository.models import FixedLicense

from task.models import Task

from tagging.fields import TagField
from tagging.models import Tag
from tagging.models import TaggedItem
from tagging.utils import calculate_cloud

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
    @cvar score: score file
    @type score: models.FileField
    @cvar task: related Task
    @type task: Task
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
    score = models.FileField(upload_to=SCOREPATH)
    task = models.ForeignKey(Task)
    license = models.ForeignKey(FixedLicense, editable=False)
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

    def get_completeness_properties(self):
        return ['tags', 'description', 'summary', 'urls', 'publications',
            'feature_processing', 'parameters', 'os', 'code',
            'software_packages', 'score']

class SolutionRating(Rating):
    """Rating for a Solution item."""
    repository = models.ForeignKey(Solution)
