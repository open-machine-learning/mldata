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

