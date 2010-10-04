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

    def get_filename(self):
        """Construct filename for Task file.

        @return: filename for Task file
        @rtype: string
        @raise AttributeError: if slug is not set.
        """
        if not self.slug_id:
            raise AttributeError, 'Attribute slug is not set!'

        return ml2h5.fileformat.get_filename(self.slug.text)


    def save(self, update_file=False, taskfile=None, silent_update=False):
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

        if silent_update:
            super(Task, self).save(silent_update=True)
        else:
            super(Task, self).save()

        if update_file or is_new:
            fname = os.path.join(MEDIA_ROOT, self.file.name)
            ml2h5.task.create(fname, self, taskfile)

    def get_completeness_properties(self):
        return ['tags', 'description', 'summary', 'urls', 'publications',
            'input', 'output', 'performance_measure', 'type', 'file']

    def get_related_data(self):
        return self.data

    def get_challenges(self, user=None):
        qs=self.get_public_qs(user)
        return self.challenge_set.filter(qs)

    def get_extract(self):
        return ml2h5.task.get_extract(os.path.join(MEDIA_ROOT, self.file.name))


class TaskRating(Rating):
    """Rating for a Task item."""
    repository = models.ForeignKey(Task)

    class Meta:
        app_label = 'repository'



