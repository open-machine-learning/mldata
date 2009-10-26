import re
from django.forms import *
from django.utils.translation import ugettext as _
from repository.models import *
from repository.widgets import AutoCompleteTagInput
from tagging.forms import TagField


class DataForm(ModelForm):
    tags = TagField(widget=AutoCompleteTagInput(), required=False)
    file = FileField(required=False)
    format = CharField(required=False)

    class Meta:
        model = Data
        exclude = ('pub_date', 'version', 'slug', 'author',)

    def clean_name(self):
        if re.match('^\d+$', self.cleaned_data['name']):
            raise ValidationError(
                _('Names consisting of only numerical values are not allowed.'))
        return self.cleaned_data['name']


class RatingForm(forms.Form):
    features = IntegerField(widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))
    usability = IntegerField(widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))
    documentation = IntegerField(widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))


