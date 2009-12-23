"""
Form classes used in app Repository
"""

import re
from django.forms import *
from django.db.models import Q
from django.db import IntegrityError
from django.utils.translation import ugettext as _
from repository.models import *
from repository.widgets import *
from tagging.forms import TagField
from settings import TAG_SPLITSTR


class RepositoryForm(forms.ModelForm):
    """Base class for item types Data, Task and Solution.

    @cvar tags: an input field with its contents autocompleted
    @type tags: tagging.forms.TagField
    """
    tags = TagField(widget=AutoCompleteTagInput(), required=False)


    def clean_name(self):
        """Cleans field name."""
        if re.match('^\d+$', self.cleaned_data['name']):
            raise ValidationError(
                _('Names consisting of only numerical values are not allowed.'))
        return self.cleaned_data['name']


    def clean_tags(self):
        """Cleans field tags.

        We want to avoid tags like 'foo, bar baz'
        """
        tags = self.cleaned_data['tags']
        return TAG_SPLITSTR.join([y for x in tags.split(' ') for y in x.split(',') if y])



class DataForm(RepositoryForm):
    """Form class for Data.

    @cvar file: is not required in form (but in model)
    @type file: forms.FileField
    """
    file = forms.FileField(required=False)

    class Meta:
        """Inner meta class to specify model and exclude options.

        @cvar model: model to use
        @type model: models.Data
        @cvar exclude: which fields to exclude in form validation
        @type exclude: list
        """
        model = Data
        exclude = ('pub_date', 'version', 'slug', 'user', 'format',)

    def __init__(self, *args, **kwargs):
        """Initialize DataForm.

        request is not needed in DataForm.
        """
        if kwargs.has_key('request'):
            kwargs.pop('request')
        super(RepositoryForm, self).__init__(*args, **kwargs)


class TaskForm(RepositoryForm):
    """Form class for Task.

    @cvar splits: is not required in form (but in model)
    @type splits: forms.FileField
    @cvar type: needs a specific queryset for TaskType
    @type type: forms.ModelChoiceField
    @cvar freeformtype: user can also specify a new TaskType in this input field
    @type freeformtype: forms.CharField
    """
    splits = forms.FileField(required=False)
    type = forms.ModelChoiceField(queryset=TaskType.objects.all(), required=False)
    freeformtype = forms.CharField(required=False)

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
            qs = Data.objects.filter(
                Q(is_approved=True) & Q(is_deleted=False) &
                (Q(user=request.user) | Q(is_public=True))
            )
            self.fields['data'].queryset = qs
            self.fields['data'].choices =\
                [(d.id, d.name + ' (v' + str(d.version) + ')') for d in qs]


    def clean_freeformtype(self):
        """Override type from freeformtype.
        """
        fftype = None
        if 'freeformtype' in self.cleaned_data:
            fftype = self.cleaned_data['freeformtype'].strip()

        if fftype:
            try:
                t = TaskType(name=fftype)
                t.save()
            except IntegrityError: # already exists
                t = TaskType.objects.get(name=fftype)
            self.cleaned_data['type'] = t
        elif not ('type' in self.cleaned_data and self.cleaned_data['type']):
            raise ValidationError(_('No type given.'))

        return fftype



class SolutionForm(RepositoryForm):
    """Form class for Solution.

    @cvar score: is not required in form (but in model)
    @type score: forms.FileField
    """
    score = forms.FileField(required=False)

    class Meta:
        """Inner meta class to specify model and exclude options.

        @cvar model: model to use
        @type model: models.Solution
        @cvar exclude: which fields to exclude in form validation
        @type exclude: list
        """
        model = Solution
        exclude = ('pub_date', 'version', 'slug', 'user',)


    def __init__(self, *args, **kwargs):
        """Initialize TaskForm.

        Filter available choices of Task items.
        """
        if kwargs.has_key('request'):
            request = kwargs.pop('request')
        else:
            request = None
        # super needs to be called before to have attribute fields
        super(RepositoryForm, self).__init__(*args, **kwargs)
        if request:
            qs = Task.objects.filter(
                Q(is_deleted=False) &
                (Q(user=request.user) | Q(is_public=True))
            )
            self.fields['task'].queryset = qs
            self.fields['task'].choices =\
                [(t.id, t.name + ' (v' + str(t.version) + ')') for t in qs]



class RatingForm(forms.Form):
    """Form used for rating an item.

    @cvar interesting: radio selection of values 0 to 5 if an item is interesting
    @type interesting: forms.IntegerField
    @cvar documentation: radio selection of values 0 to 5 if an item is well documented
    @type documentation: forms.IntegerField
    """
    interesting = forms.IntegerField(widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))
    documentation = forms.IntegerField(widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))
