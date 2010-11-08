from django.db import models
from django.core.urlresolvers import reverse

from repository.models import Repository
from repository.models import Rating
from repository.models import FixedLicense

from tagging.fields import TagField
from task import Task
from challenge import Challenge
from django.utils.translation import ugettext as _

from utils import slugify

from mleval import evaluation
import ml2h5
import os
import numpy

from settings import SOLUTIONPATH, MEDIA_ROOT

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

    def get_related_results(self):
        from repository.models.solution import Result
        return Result.objects.filter(solution=self.pk)

class SolutionRating(Rating):
    """Rating for a Solution item."""
    repository = models.ForeignKey(Solution)

    class Meta:
        app_label = 'repository'

class Result(models.Model):
    """Repository item Result.

    @cvar score: score file
    @type score: models.FileField
    """

    pub_date = models.DateTimeField(auto_now=True, auto_now_add=True)
    task = models.ForeignKey(Task)
    solution = models.ForeignKey(Solution)
    challenge = models.ForeignKey(Challenge, blank=True, null=True)
    output_file = models.FileField(upload_to=SOLUTIONPATH)
    aggregation_score = models.FloatField(default=-1, blank=True)
    complex_result= models.TextField(null=True, blank=True)
    complex_result_type = models.CharField(max_length=255, null=True, blank=True)

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

    def get_output_filename(self):
        return os.path.join(MEDIA_ROOT, SOLUTIONPATH, self.output_file.name)

    def predict(self):
        """Evaluate performance measure.

        @return: score, message, ok flag
        @rtype: string
        """
        try:
            fname_task = self.task.get_task_filename()
            test_idx, output_variables = ml2h5.task.get_test_output(fname_task)
        except:
            return -1,_("Couldn't get information from Task file!"), False

        try:
            fname_data = self.task.data.get_data_filename()
            correct = ml2h5.data.get_correct(fname_data, test_idx, output_variables)
        except Exception:
            return -1,_("Couldn't extract true outputs from Data file!"), False

        try:
            data = self.output_file.read()
        except Exception:
            return -1,_("Failed to read predictions"), False

        try:
            predicted = [float(d) for d in data.split("\n") if d]
        except ValueError:
            predicted = [d for d in data.split("\n") if d]
        except Exception:
            return -1,_("Format of given results is wrong!"), False

        data=numpy.array(data)
        predicted=numpy.array(predicted)
        correct = numpy.array(correct)

        len_p = len(predicted)
        len_c = len(correct)
        if len_p != len_c:
            return -1,_("Length of correct results and submitted results doesn't match, expected %d, got %d") % (len_c, len_p), False

        try:
            t=self.task.type
            pm=self.task.performance_measure
            measure=evaluation.pm_hierarchy[t][pm][0]
            score = measure(predicted, correct)
            try:
                s=score[0]
            except:
                s=score

            return score, _('%s, %s: %2.2f %%') % (t, pm, s), True
        except Exception, e:
            return -1, str(e), False


    class Meta:
        app_label = 'repository'
