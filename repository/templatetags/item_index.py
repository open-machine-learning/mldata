from django import template
from urllib import quote

register = template.Library()
@register.inclusion_tag('repository/item_index_common.html', takes_context=True)

def item_index(context, queryset, klass):
    pname=klass.lower() + '_page'
    r= {
            'klass': klass,
            pname: queryset,
            'page': queryset,
            'page_name': pname,
        }
    if context.has_key('searchterm'):
        r['searchterm']=quote(context['searchterm'],'')
        r['selecttab']='#tabs-' + klass.lower()
    if context.has_key('klass'):
        r['klass']=quote(context['klass'],'')
    if context.has_key('tagcloud'):
        r['tagcloud']=context['tagcloud']
    return r
