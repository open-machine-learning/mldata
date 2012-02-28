import re
from django.core.urlresolvers import reverse
from django.forms import *
from django.db.models import Q
from django.db import IntegrityError
from django.utils.translation import ugettext as _
from django.http import HttpResponseRedirect

import ml2h5.task
import ml2h5.converter

from repository.models import *
from repository.widgets import *
from repository.forms import RepositoryForm
from tagging.forms import TagField

from repository.models import Data

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
        if format in ml2h5.converter.TO_H5:
            self.fields['convert'].initial = True
        else:
            self.fields['convert'].initial = False


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
