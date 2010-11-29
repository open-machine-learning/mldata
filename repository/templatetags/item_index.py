from django import template
from urllib import quote
from repository.views.base import DOWNLOAD_WARNING_LIMIT

register = template.Library()
@register.inclusion_tag('repository/item_index_common.html', takes_context=True)

def item_index(context, queryset, klass):
    pname=klass.lower() + '_page'
    r= {
            'klass': klass,
            pname: queryset,
            'page': queryset,
            'page_name': pname,
            'download_warning_limit': DOWNLOAD_WARNING_LIMIT,
        }
    if context.has_key('searchterm'):
        r['searchterm']=quote(context['searchterm'],'')
        r['selecttab']='#tabs-' + klass.lower()
    if context.has_key('klass'):
        r['klass']=quote(context['klass'],'')
    if context.has_key('tagcloud'):
        r['tagcloud']=context['tagcloud']
    return r
