"""
Widgets used in forms in Repository

@var MAX_ITEMS: maximum number of tags in autocomplete list
@type MAX_ITEMS: integer
"""

from django import forms
from django.utils import simplejson
from django.utils.safestring import mark_safe
from tagging.models import Tag
from repository.models import *

MAX_ITEMS = 23


class AutoCompleteInput(forms.TextInput):
    """Implements autocompletion for a forms.TextInput field."""

    class Media:
        """Inner class to handle includes.

        @cvar css: stylesheet to include
        @type css: dict
        @cvar js: javascripts to include
        @type js: list
        """
        css = {
            'all': ('css/jquery.autocomplete.css',)
        }
        js = (
            'js/jquery/jquery.js',
            'js/jquery/jquery.bgiframe.min.js',
            'js/jquery/jquery.ajaxQueue.js',
            'js/jquery/jquery.autocomplete.js'
        )

    def get_snippet(self, output, id, object_list, multiple=True):
        """Get a Javascript snippet to be included in the widget at the right
        place.

        @param output: previous HTML code
        @type output: string
        @param id: DOM id of widget
        @type id: string
        @param object_list: list of items (e.g. tags)
        @type object_list: string
        @param multiple: if multiple items are allowed to be used
        @type multiple: boolean
        @return: an HTML snippet as part of the whole widget
        @rtype: string
        """
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
            </script>''' % (id, object_list, MAX_ITEMS, str(multiple).lower()))


class AutoCompleteTagInput(AutoCompleteInput):
    """Implements an autocompletion widget for tags."""
    def render(self, id, value, attrs=None):
        """Render the widget.

        @param id: DOM id of the widget
        @type id: string
        @param value: some value...
        @type value: unknown
        @param attrs: some attributes
        @type attrs: unknown
        @return: the completely rendered widget
        @rtype: string
        """
        output = super(AutoCompleteTagInput, self).render(id, value, attrs)
        tags = Tag.objects.all()
        tag_list = simplejson.dumps([tag.name for tag in tags],
                                    ensure_ascii=False)
        return self.get_snippet(output, id, tag_list)

#class AutoCompleteLicenseInput(AutoCompleteInput):
#    def render(self, name, value, attrs=None):
#        output = super(AutoCompleteLicenseInput, self).render(name, value, attrs)
#        licenses = set(Data.objects.values_list('license', flat=True))
#        license_list = simplejson.dumps(
#            [l for l in licenses if l], ensure_ascii=False)
#        return self.get_snippet(output, name, license_list, multiple=False)

