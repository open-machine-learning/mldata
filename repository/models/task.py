from django.db import models
from django.core.urlresolvers import reverse
from gettext import gettext as _


from settings import TASKPATH

from repository.models import Slug
from repository.models import Repository
from repository.models import Rating
from repository.models import FixedLicense

from tagging.fields import TagField
from tagging.models import Tag
from tagging.models import TaggedItem
from tagging.utils import calculate_cloud

from data import Data

from utils import slugify

import os
import ml2h5
from settings import MEDIA_ROOT

class TaskPerformanceMeasure(models.Model):
    """Performance measure (evaluation function) of a Task.

    @cvar name: name of the evaluation function
    @type name: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        app_label = 'repository'

    def __unicode__(self):
        return unicode(self.name)

class TaskType(models.Model):
    """Type of a Task.

    @cvar name: name of the type
    @type name: string / models.CharField
    """
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        app_label = 'repository'

    def __unicode__(self):
        return unicode(self.name)

class Task(Repository):
    """Repository item Task.

    @cvar input: item's input format
    @type input: string / models.TextField
    @cvar output: item's output format
    @type output: string / models.TextField
    @cvar performance_measure: performance measure (evaluation function)
    @type performance_measure: TaskPerformanceMeasure
    @cvar performance_ordering: true => up, false => down
    @type performance_ordering: boolean / models.BooleanField
    @cvar type: item's type, e.g. Regression, Classification
    @type type: TaskType
    @cvar data: related Data item
    @type data: Data / models.ForeignKey
    @cvar data_heldback: another optional, possibly private, Data item for challenge organisers
    @type data_heldback: Data / models.ForeignKey
    @cvar file: the Task file with splits, targets, features
    @type file: models.FileField
    @cvar license: item's license
    @type license: FixedLicense
    @cvar tags: item's tags
    @type tags: string / tagging.TagField
    """
    input = models.TextField()
    output = models.TextField()
    performance_measure = models.ForeignKey(TaskPerformanceMeasure)
    performance_ordering = models.BooleanField()
    type = models.ForeignKey(TaskType)
    data = models.ForeignKey(Data, related_name='task_data')
    data_heldback = models.ForeignKey(Data, related_name='task_data_heldback', null=True, blank=True)
    file = models.FileField(upload_to=TASKPATH)
    license = models.ForeignKey(FixedLicense, editable=False)
    tags = TagField() # tagging doesn't work anymore if put into base class

    class Meta:
        app_label = 'repository'

    def get_media_path(self):
        return os.path.join(MEDIA_ROOT, self.file.name)

    def _find_dset_offset(self, contents, output_variables):
        """Find the dataset in given contents that contains the
        output_variable(s).

        This would be easy if all the data was just in one blob, but it may be
        in several datasets as defined by contents['ordering'], e.g. in
        contents['label'] or contents['data'] or contents['nameofvariable'].

        @param contents: contents of a Data file
        @type contents: dict
        @param output_variables: index of output_variables to look for
        @type output_variables: integer
        @return: dataset and offset in that dataset corresponding to
        output_variables
        @rtype: list of list and integer
        """
        ov = output_variables
        for name in contents['ordering']:
            try:
                for i in xrange(len(contents[name][0])):
                    if ov == 0:
                        return contents[name], i
                    else:
                        ov -= 1
            except: # dataset has only 1 variable as a list, not as array
                if ov == 0:
                    return contents[name], 0
                else:
                    ov -= 1

        return None, None

    def predict(self, data):
        """Evaluate performance measure of given item through given data.

        @param data: uploaded result data
        @type data: string
        @return: the computed score with descriptive text
        @rtype: string
        """
        try:
            fname_task = os.path.join(MEDIA_ROOT, self.file.name)
            test_idx, output_variables = ml2h5.task.get_test_output(fname_task)
        except:
            return _("Couldn't get information from Task file!"), False

        try:
            fname_data = os.path.join(MEDIA_ROOT, self.data.file.name)
            correct = ml2h5.data.get_correct(fname_data, test_idx, output_variables)
        except:
            return _("Couldn't get correct results from Data file!"), False

        try:
            predicted = [float(d) for d in data.split("\n") if d]
        except ValueError:
            predicted = [d for d in data.split("\n") if d]
        except:
            return _("Format of given results is wrong!"), False

        len_p = len(predicted)
        len_c = len(correct)
        if len_p != len_c:
            return _("Length of correct results and submitted results doesn't match, %d != %d") % (len_c, len_p), False

        if self.performance_measure.id == 2:
            from utils.performance_measure import ClassificationErrorRate as PM
            formatstr = _('Error rate: %.2f %%')
        elif self.performance_measure.id == 3:
            from utils.performance_measure import RegressionMAE as PM
            formatstr = _('Mean Absolute Error: %f')
        elif self.performance_measure.id == 4:
            from utils.performance_measure import RegressionRMSE as PM
            formatstr = _('Root Mean Squared Error: %f')
        else:
            return _("Unknown performance measure!"), False

        try:
            score = PM().run(correct, predicted)
            return formatstr % score, True
        except Exception, e:
            return str(e), False

    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        @return: an absolute URL or None
        @rtype: string
        """
        view = 'repository.views.task.view_slug'
        return reverse(view, args=[self.task.data.slug.text, self.slug.text])

    def get_filename(self):
        """Construct filename for Task file.

        @return: filename for Task file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        return ml2h5.fileformat.get_filename(self.slug.text)


    def save(self, update_file=False, taskfile=None):
        """Save Task item, also updates Task file.

        @param update_file: if Task file should be updated on save
        @type update_file: boolean
        @param taskfile: data to write to Task file
        @type taskfile: dict with indices train_idx, test_idx, input_variables, output_variables
        """
        is_new = False
        if not self.file.name:
            self.file.name = os.path.join(TASKPATH, self.get_filename())
            is_new = True
        super(Task, self).save()

        if update_file or is_new:
            fname = os.path.join(MEDIA_ROOT, self.file.name)
            ml2h5.task.create(fname, self, taskfile)

    def qs_for_related(self):
        return self.solution_set

    def get_completeness_properties(self):
        return ['tags', 'description', 'summary', 'urls', 'publications',
            'input', 'output', 'performance_measure', 'type', 'file']

    def get_related_data(self):
        return self.data

    def get_extract(self):
        return ml2h5.task.get_extract(os.path.join(MEDIA_ROOT, self.file.name))


class TaskRating(Rating):
    """Rating for a Task item."""
    repository = models.ForeignKey(Task)

    class Meta:
        app_label = 'repository'



