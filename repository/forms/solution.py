from django.forms import *
from django.db.models import Q

from repository.forms import RepositoryForm

from repository.models import *
from repository.widgets import *

from repository.models import Solution
from repository.models import Result


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
