from django.db import models
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _


from settings import TASKPATH, MEDIA_ROOT

import repository
from repository.models import Slug, Repository, Rating, FixedLicense

from tagging.fields import TagField
from tagging.models import Tag
from tagging.models import TaggedItem
from tagging.utils import calculate_cloud

from data import Data
from utils import slugify

import os
import ml2h5

class Task(Repository):
    """Repository item Task.

    @cvar input: item's input format
    @type input: string / models.TextField
    @cvar output: item's output format
    @type output: string / models.TextField
    @cvar performance_measure: performance measure (evaluation function)
    @type performance_measure: string / name
    @cvar type: item's type, e.g. Regression, Classification
    @type type: string
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
    performance_measure = models.CharField(max_length=255)
    type = models.CharField(max_length=255)
    data = models.ForeignKey(Data, related_name='task_data')
    data_heldback = models.ForeignKey(Data, related_name='task_data_heldback', null=True, blank=True)
    file = models.FileField(upload_to=TASKPATH)
    license = models.ForeignKey(FixedLicense, editable=False)
    tags = TagField() # tagging doesn't work anymore if put into base class

    class Meta:
        app_label = 'repository'

    def get_task_filename(self):
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

    def get_absolute_slugurl(self):
        """Get absolute URL for this item, using its slug.

        @return: an absolute URL or None
        @rtype: string
        """
        view = 'repository.views.task.view_slug'
        return reverse(view, args=[self.slug.text])

    def get_absolute_slugurlver(self):
        """Get absolute URL for this item, using its slug and version.

        @return: an absolute URL or None
        @rtype: string
        """
        view = 'repository.views.task.view_slug'
        return reverse(view, args=[self.slug.text, self.version])

    def get_filename(self):
        """Construct filename for Task file.

        @return: filename for Task file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        return ml2h5.fileformat.get_filename('%s_v%d' % (self.slug.text, self.version))

    def create_next_file(self, prev):
        if self.file:
            filename = os.path.join(MEDIA_ROOT, self.file.name)
            taskinfo = ml2h5.task.get_taskinfo(filename)
            try:
                os.remove(filename)
            except:
                pass
            self.save(taskinfo)
        else:
            if not prev:
                return

            prev_filename = os.path.join(MEDIA_ROOT, prev.file.name)
            self.file = prev.file
            self.file.name = os.path.join(TASKPATH, self.get_filename())
            next_filename = os.path.join(MEDIA_ROOT, self.file.name)
            os.link(prev_filename, next_filename)

    def save(self, taskinfo=None, silent_update=False):
        """Save Task item, also updates Task file.

        @param taskinfo: data to write to Task file
        @type taskinfo: dict with indices train_idx, test_idx, input_variables, output_variables
        """

        if taskinfo:
            self.file.name = os.path.join(TASKPATH, self.get_filename())
            fname = os.path.join(MEDIA_ROOT, self.file.name)
            ml2h5.task.update_or_create(fname, self, taskinfo)

        super(Task, self).save(silent_update=silent_update)

    def get_completeness_properties(self):
        return ['tags', 'description', 'summary', 'urls', 'publications',
            'input', 'output', 'performance_measure', 'type', 'file']

    def get_data(self):
        return self.data

    def get_related_methods(self):
        from repository.models.method import Result
        return Result.objects.filter(task=self.pk)

    def get_challenges(self, user=None):
        qs=self.get_public_qs(user)
        return self.challenge_set.filter(qs)

    def get_extract(self):
        return ml2h5.task.get_extract(os.path.join(MEDIA_ROOT, self.file.name))

    def dependent_entries_exist(self):
        """Check whether there exists an object which depends on self.

        for Task objects, checks whether there exists a Challenge or Result object.
        """
        if repository.models.Challenge.objects.filter(task__slug=self.slug).count() > 0:
            return True
        if repository.models.Result.objects.filter(task__slug=self.slug).count() > 0:
            return True
        return False

    def has_h5(self):
        return self.get_task_filename().endswith('.h5')
    def can_convert_to_octave(self):
        return ml2h5.fileformat.can_convert_h5_to('octave', self.get_task_filename())
    def can_convert_to_rdata(self):
        return ml2h5.fileformat.can_convert_h5_to('rdata', self.get_task_filename())
    def can_convert_to_matlab(self):
        return ml2h5.fileformat.can_convert_h5_to('matlab', self.get_task_filename())


class TaskRating(Rating):
    """Rating for a Task item."""
    repository = models.ForeignKey(Task)

    class Meta:
        app_label = 'repository'



