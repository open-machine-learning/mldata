"""
Form classes used in app Repository
"""

import re
from django.core.urlresolvers import reverse
from django.forms import *
from django.db.models import Q
from django.db import IntegrityError
from django.utils.translation import ugettext as _
from repository.models import *
from repository.widgets import *
from tagging.forms import TagField
from settings import TAG_SPLITSTR
from django.http import HttpResponseRedirect

attrs_checkbox = { 'class': 'checkbox' }

class RepositoryForm(forms.ModelForm):
    """Base class for item types Data, Task and Solution.

    @cvar tags: an input field with its contents autocompleted
    @type tags: tagging.forms.TagField
    """
    tags = TagField(widget=AutoCompleteTagInput(), required=False)
    keep_private = BooleanField(
        widget=forms.CheckboxInput(attrs=attrs_checkbox), required=False)


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

    @cvar file: is not required in form (but in model)
    @type file: forms.FileField
    @cvar type: needs a specific queryset for TaskType
    @type type: forms.ModelChoiceField
    @cvar freeformtype: user can also specify a new TaskType in this input field
    @type freeformtype: forms.CharField
    """
    file = forms.FileField(required=False)
    type = forms.ModelChoiceField(queryset=TaskType.objects.all(), required=False)
    freeformtype = forms.CharField(required=False)
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


    def clean_input_variables(self):
        """Ensure input variables are given as comma-seperated list."""
        if 'input_variables' in self.cleaned_data:
            if not self.cleaned_data['input_variables']:
                return None
            try:
                return [int(x) for x in self.cleaned_data['input_variables'].split(',')]
            except:
                raise ValidationError(_('Not a comma-seperated list of integers.'))


    def clean_output_variables(self):
        """Ensure output variables is one integer."""
        if 'output_variables' in self.cleaned_data:
            if not self.cleaned_data['output_variables']:
                return None
            try:
                return int(self.cleaned_data['output_variables'])
            except:
                raise ValidationError(_('Not a single integer.'))



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
        """Initialize SolutionForm.

        Filter available choices of Task items.
        """
        if kwargs.has_key('request'):
            request = kwargs.pop('request')
        else:
            request = None
        # super needs to be called before to have attribute fields
        super(RepositoryForm, self).__init__(*args, **kwargs)
        if request:
            cv = Task.objects.filter(Q(is_current=True) &
                (Q(user=request.user) | Q(is_public=True))
            )
            ids = [t.id for t in cv]
            qs = Task.objects.filter(pk__in=ids)
            self.fields['task'].queryset = qs
            self.fields['task'].choices = [(t.id, t.name) for t in qs]



class RatingForm(forms.Form):
    """Form used for rating an item.

    @cvar interest: radio selection of values 0 to 5 if an item is interesting
    @type interest: forms.IntegerField
    @cvar doc: radio selection of values 0 to 5 if an item is well documented
    @type doc: forms.IntegerField
    """
    interest = forms.IntegerField(label=_("Interesting"), widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))
    doc = forms.IntegerField(label=_("Documentation"), widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))

    @staticmethod
    def get(request, obj):
        """Get a rating form for given item.

        @param request: request data
        @type request: Django request
        @param obj: item to get rating form for
        @type obj: either of Data, Task, Solution
        @return: a rating form
        @rtype: forms.RatingForm
        """
        if not request.user.is_authenticated():
            return None

        current = obj.__class__.objects.get(slug=obj.slug, is_current=True)
        if not current:
            return None

        klassname = current.__class__.__name__
        rklass = eval(klassname + 'Rating')
        try:
            r = rklass.objects.get(user=request.user, repository=current)
            form = RatingForm({'interest': r.interest, 'doc': r.doc})
        except rklass.DoesNotExist:
            form = RatingForm()

        form.action = reverse('repository_' + klassname.lower() + '_rate', args=[current.id])
        return form


class PublicationForm(forms.ModelForm):
    """Form used for publications."""
    id = forms.IntegerField()
    next = forms.CharField()

    class Meta:
        """Inner meta class to specify model options.

        @cvar model: model to use
        @type model: models.Publication
        """
        model = Publication


class DataReviewForm(forms.Form):
    """Form used for Data review."""
    format = forms.CharField(required=True)
    seperator = forms.CharField(required=False, max_length=1)
    attribute_names_first = BooleanField(required=False)
    convert = BooleanField(required=False)


    def prefill(self, format, seperator):
        """Prefill form fields aided by given arguments.

        @param format: format of data file
        @type format: string
        @param seperator: seperator for attributes used in data files
        @type seperator: string
        """
        self.fields['format'].initial = format
        if format == 'h5':
            self.fields['seperator'].initial = ''
        else:
            self.fields['seperator'].initial = seperator
        if format in ('h5', 'xml', 'unknown'):
            self.fields['convert'].initial = False
        else:
            self.fields['convert'].initial = True


    def clean_format(self):
        """Lowercase variable format."""
        if 'format' in self.cleaned_data:
            return self.cleaned_data['format'].lower()
        else:
            raise ValidationError(_('No format specified.'))


    def clean_seperator(self):
        """Accept no seperator when format is h5."""
        if 'format' in self.cleaned_data:
            if 'seperator' in self.cleaned_data:
                return self.cleaned_data['seperator']
            elif self.cleaned_data['format'] == 'h5':
                return ''
            else:
                raise ValidationError(_('No seperator specified.'))
        else:
            raise ValidationError(_('No format specified.'))

