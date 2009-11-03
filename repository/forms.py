import re
from django.forms import *
from django.utils.translation import ugettext as _
from repository.models import *
from repository.widgets import *
from tagging.forms import TagField
from settings import TAG_SPLITCHAR


class DataForm(ModelForm):
    tags = TagField(widget=AutoCompleteTagInput(), required=False)
    file = FileField(required=False)
    format = CharField(required=False)
#    license = CharField(widget=AutoCompleteLicenseInput())

    class Meta:
        model = Data
        exclude = ('pub_date', 'version', 'slug', 'user',)

    def clean_name(self):
        if re.match('^\d+$', self.cleaned_data['name']):
            raise ValidationError(
                _('Names consisting of only numerical values are not allowed.'))
        return self.cleaned_data['name']

    def clean_tags(self): # avoid tags like 'foo, bar baz'
        tags = self.cleaned_data['tags']
        return TAG_SPLITCHAR.join([y for x in tags.split(' ') for y in x.split(',') if y])


class RatingForm(forms.Form):
    interesting = IntegerField(widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))
    documentation = IntegerField(widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))


