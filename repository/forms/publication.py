from django import forms
from repository.models import Publication

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
