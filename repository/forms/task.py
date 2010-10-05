import re
from django.core.urlresolvers import reverse
from django.forms import *
from django.db.models import Q
from django.db import IntegrityError
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect

import ml2h5.task
from ml2h5.indexsplit import expand_split_str,check_split_str
from  mleval import evaluation

from settings import TAG_SPLITSTR

from repository.models import *
from repository.widgets import *
from repository.forms import RepositoryForm
from tagging.forms import TagField

from repository.models import Data, Task

def extract_choices():
    choices=[]
    for t in evaluation.pm_hierarchy.keys():
        choices.extend([ (x,x) for x in evaluation.pm_hierarchy[t].keys() ])
    choices.sort()
    return choices

def extract_types():
    types=[(x,x) for x in evaluation.pm_hierarchy.keys()]
    types.sort()
    return types

class TaskForm(RepositoryForm):
    """Form class for Task.

    @cvar file: is not required in form (but in model)
    @type file: forms.FileField
    @cvar type: needs a specific queryset for TaskType
    @type type: forms.ModelChoiceField
    @cvar freeformtype: user can also specify a new TaskType in this input field
    @type freeformtype: forms.CharField
    """
    file = forms.FileField(required=False)
    performance_measure = forms.ChoiceField(choices= \
        extract_choices(), required=True)
    type = forms.ChoiceField(choices=extract_types(),
            initial='Binary Classification', required=True)
    train_idx = forms.CharField(required=False)
    test_idx = forms.CharField(required=False)
    input_variables = forms.CharField(required=False)
    output_variables = forms.CharField(required=False)


    class Meta:
        """Inner meta class to specify model and exclude options.

        @cvar model: model to use
        @type model: models.Task
        @cvar exclude: which fields to exclude in form validation
        @type exclude: list
        """
        model = Task
        exclude = ('pub_date', 'version', 'slug', 'user')

    def __init__(self, *args, **kwargs):
        """Initialize TaskForm.

        Filter available choices of Data items.
        """
        if kwargs.has_key('request'):
            request = kwargs.pop('request')
        else:
            request = None
        # super needs to be called before to have attribute fields
        super(RepositoryForm, self).__init__(*args, **kwargs)
        if request:
            cv = Data.objects.filter(Q(is_current=True) &
                Q(is_approved=True) &
                (Q(user=request.user) | Q(is_public=True))
            )
            ids = [d.id for d in cv]
            qs = Data.objects.filter(pk__in=ids)
            self.fields['data'].queryset = qs
            self.fields['data_heldback'].queryset = qs
            choices = [(d.id, d.name) for d in qs]
            self.fields['data'].choices = choices
            choices.insert(0, ('', '---------'))
            #choices.append(('', '-----'))
            self.fields['data_heldback'].choices = choices


    def prefill(self, fname):
        """Prefill form with values from Task file.

        @param fname: name of Task file
        @type fname: string
        """
        extract = ml2h5.task.get_extract(fname)
        for name in extract.keys():
            try:
                self.fields[name].initial = ','.join([str(d) for d in extract[name]])
            except TypeError:
                self.fields[name].initial = str(extract[name])



    def _clean_valid_inputformat(self, name):
        """Ensure field with given name has a valid format.

        @param name: name of field to clean
        @type name: string
        @return: list of integers
        @rtype: list of integers
        """
        if name in self.cleaned_data:
            if not self.cleaned_data[name]:
                return None
	    if check_split_str(self.cleaned_data[name]): 
                return [int(x) for x in expand_split_str(self.cleaned_data[name])]
	    else:
		    raise ValidationError(_('Invalid Format (smpl: 1,2,3:5).'))

    def clean_train_idx(self):
        """Ensure train_idx are given as comma-seperated list of integers."""
        return self._clean_valid_inputformat('train_idx')
    def clean_test_idx(self):
        """Ensure test_idx are given as comma-seperated list of integers."""
        return self._clean_valid_inputformat('test_idx')
    def clean_input_variables(self):
        """Ensure input variables are given as comma-seperated list of integers."""
        return self._clean_valid_inputformat('input_variables')


    def clean_output_variables(self):
        """Ensure output variables is one integer."""
        if 'output_variables' in self.cleaned_data:
            if not self.cleaned_data['output_variables']:
                return None
            try:
                return int(self.cleaned_data['output_variables'])
            except:
                raise ValidationError(_('Not a single integer.'))

