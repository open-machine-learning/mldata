from django.forms import *
from django.db.models import Q

from repository.forms import RepositoryForm

from repository.models import *
from repository.widgets import *

class ChallengeForm(RepositoryForm):
    """Form class for Challenge.
    """
    task= forms.ModelMultipleChoiceField(queryset=Task.objects.all(), required=True)

    class Meta:
        """Inner meta class to specify model and exclude options.

        @cvar model: model to use
        @type model: models.Challenge
        @cvar exclude: which fields to exclude in form validation
        @type exclude: list
        """
        model = Challenge
        exclude = ('pub_date', 'version', 'slug', 'user',)


    def __init__(self, *args, **kwargs):
        """Initialize ChallengeForm.

        Filter available choices of Task items.
        """
        if kwargs.has_key('request'):
            request = kwargs.pop('request')
        else:
            request = None
        # super needs to be called before to have attribute fields
        super(RepositoryForm, self).__init__(*args, **kwargs)

#        if request:
#            cv = Task.objects.filter(Q(is_current=True) &
#                (Q(user=request.user) | Q(is_public=True))
#            )
#            ids = [t.id for t in cv]
#            qs = Task.objects.filter(pk__in=ids)
#            self.fields['task'].queryset = qs
#            self.fields['task'].choices = [(t.id, t.name) for t in qs]
