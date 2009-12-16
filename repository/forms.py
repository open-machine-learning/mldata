import re
from django.forms import *
from django.db.models import Q
from django.utils.translation import ugettext as _
from repository.models import *
from repository.widgets import *
from tagging.forms import TagField
from settings import TAG_SPLITCHAR


class DataForm(ModelForm):
    tags = TagField(widget=AutoCompleteTagInput(), required=False)
    file = FileField(required=False)

    class Meta:
        model = Data
        exclude = ('pub_date', 'version', 'slug', 'user', 'format',)

    def clean_name(self):
        if re.match('^\d+$', self.cleaned_data['name']):
            raise ValidationError(
                _('Names consisting of only numerical values are not allowed.'))
        return self.cleaned_data['name']

    def clean_tags(self): # avoid tags like 'foo, bar baz'
        tags = self.cleaned_data['tags']
        return TAG_SPLITCHAR.join([y for x in tags.split(' ') for y in x.split(',') if y])



class TaskForm(ModelForm):
    tags = TagField(widget=AutoCompleteTagInput(), required=False)
    splits = FileField(required=False)

    class Meta:
        model = Task
        exclude = ('pub_date', 'version', 'slug', 'user',)

    def __init__(self, *args, **kwargs):
        # filter available choices for Data item
        if kwargs.has_key('request'):
            request = kwargs.pop('request')
        else:
            request = None
        # super needs to be called before to have attribute fields
        super(ModelForm, self).__init__(*args, **kwargs)
        if request:
            qs = Data.objects.filter(
                Q(is_approved=True) & Q(is_deleted=False) &
                (Q(user=request.user) | Q(is_public=True))
            )
            self.fields['data'].queryset = qs
            self.fields['data'].choices =\
                [(d.id, d.name + ' (v' + str(d.version) + ')') for d in qs]

    def clean_name(self):
        if re.match('^\d+$', self.cleaned_data['name']):
            raise ValidationError(
                _('Names consisting of only numerical values are not allowed.'))
        return self.cleaned_data['name']

    def clean_tags(self): # avoid tags like 'foo, bar baz'
        tags = self.cleaned_data['tags']
        return TAG_SPLITCHAR.join([y for x in tags.split(' ') for y in x.split(',') if y])



class SolutionForm(ModelForm):
    class Meta:
        model = Solution
        exclude = ('pub_date', 'version', 'slug', 'user',)



class RatingForm(forms.Form):
    interesting = IntegerField(widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))
    documentation = IntegerField(widget=RadioSelect(choices=( (0, '0'), (1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5') )))


