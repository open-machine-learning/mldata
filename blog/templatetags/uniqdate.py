from django import template
from django.conf import settings

register = template.Library()

def do_uniqdate(seq, token):
    seen = {}
    result = []
    fieldname, is_obj = token.split(',')
    for item in seq:
        if eval(is_obj):
            marker = getattr(item.pub_date, fieldname)
        else:
            marker = getattr(item, fieldname)
        if marker in seen: continue
        seen[marker] = 1
        result.append(marker)
    return result

register.filter('uniqdate', do_uniqdate)
