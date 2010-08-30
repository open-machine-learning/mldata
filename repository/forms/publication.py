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


