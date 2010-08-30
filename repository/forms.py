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



