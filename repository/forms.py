from django.forms import ModelForm
from repository.models import *
from repository.widgets import AutoCompleteTagInput
from tagging.forms import TagField

class DataForm(ModelForm):
    tags = TagField(widget=AutoCompleteTagInput(), required=False)

    class Meta:
        model = Data
        exclude = ('pub_date', 'version', 'slug', 'author',)



