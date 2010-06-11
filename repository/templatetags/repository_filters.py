from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter(name='edit_if_empty')
@stringfilter
def edit_if_empty(value):
    if len(value) == 0:
        return("(No information yet)")
    else:
        value
