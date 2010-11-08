from django.db import models
from django.db.models import Q
from django.core.urlresolvers import reverse

from repository.models import Repository
from repository.models import Rating
from repository.models import FixedLicense
from task import Task

from tagging.fields import TagField
from tagging.models import Tag
from tagging.models import TaggedItem
from tagging.utils import calculate_cloud

from utils import slugify

# Create your models here.
class Challenge(Repository):
    """Repository item Challenge.

    @cvar license: item's license
    @type license: FixedLicense
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    license = models.ForeignKey(FixedLicense, editable=False)
    track = models.CharField(max_length=255, blank=True)
    task = models.ManyToManyField(Task)
    tags = TagField() # tagging doesn't work anymore if put into base class

    class Meta:
        app_label = 'repository'

    def get_completeness_properties(self):
        return ['tags', 'description', 'summary', 'urls', 'publications',
            'track']

    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        @return: an absolute URL or None
        @rtype: string
        """
        view = 'repository.views.challenge.view_slug'
        return reverse(view, args=[self.slug.text])
    
    def get_tasks(self, user=None):
        qs=self.get_public_qs(user, Q(is_current=True))
        return self.task.filter(qs)

    def get_related_solutions(self):
        from repository.models.solution import Result
        return Result.objects.filter(solution=self.pk)

class ChallengeRating(Rating):
    """Rating for a Challenge item."""
    repository = models.ForeignKey(Challenge)

    class Meta:
        app_label = 'repository'
