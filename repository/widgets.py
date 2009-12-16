from django import forms
from django.utils import simplejson
from django.utils.safestring import mark_safe
from tagging.models import Tag
from repository.models import *

MAX_ITEMS = 23


class AutoCompleteInput(forms.TextInput):
    class Media:
        css = {
            'all': ('css/jquery.autocomplete.css',)
        }
        js = (
            'js/jquery/jquery.js',
            'js/jquery/jquery.bgiframe.min.js',
            'js/jquery/jquery.ajaxQueue.js',
            'js/jquery/jquery.autocomplete.js'
        )

    def get_snippet(self, output, name, object_list, multiple=True):
        return output + mark_safe(u'''<script type="text/javascript">
            jQuery("#id_%s").autocomplete(%s, {
                width: 150,
                max: %s,
                highlight: false,
                multiple: %s,
                multipleSeparator: ", ",
                scroll: true,
                scrollHeight: 300,
                matchContains: true,
                autoFill: true,
            });
            </script>''' % (name, object_list, MAX_ITEMS, str(multiple).lower()))


class AutoCompleteTagInput(AutoCompleteInput):
    def render(self, name, value, attrs=None):
        output = super(AutoCompleteTagInput, self).render(name, value, attrs)
        tags = Tag.objects.all()
        tag_list = simplejson.dumps([tag.name for tag in tags],
                                    ensure_ascii=False)
        return self.get_snippet(output, name, tag_list)

#class AutoCompleteLicenseInput(AutoCompleteInput):
#    def render(self, name, value, attrs=None):
#        output = super(AutoCompleteLicenseInput, self).render(name, value, attrs)
#        licenses = set(Data.objects.values_list('license', flat=True))
#        license_list = simplejson.dumps(
#            [l for l in licenses if l], ensure_ascii=False)
#        return self.get_snippet(output, name, license_list, multiple=False)

