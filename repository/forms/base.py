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
import ml2h5.task


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
