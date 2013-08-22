from django import template
from urllib import quote

register = template.Library()
@register.inclusion_tag('paginator.html', takes_context=True)

def paginator(context, adjacent_pages=5):
    """
    To be used in conjunction with the object_list generic view.

    Adds pagination context variables for use in displaying first, adjacent and
    last page links in addition to those created by the object_list generic
    view.

    """

    if not context.has_key('page_name'):
        return

    page_name=context['page_name']

    if context.has_key(page_name):
        page=context[page_name]
        page_obj=page.page_obj
        if not page_obj:
            return
        page_number=page_obj.number
        page_numbers = [n for n in \
                        range(page_number - adjacent_pages, page_number + adjacent_pages + 1) \
                        if n > 0 and n <= page.num_pages]

        range_base = ((page_number - 1) * page.per_page)
        if len(page_numbers)<=1:
            page_numbers=[]

        r= {
                'hits': page.count,
                'results_per_page': page.per_page,
                'first_this_page': page_obj.start_index(),
                'last_this_page': page_obj.end_index(),
                'page_name': page_name,
                'page': page_number,
                'pages': page.num_pages,
                'page_numbers': page_numbers,
                'show_first': 1 not in page_numbers,
                'show_last': page.num_pages not in page_numbers,
                }
        if page_obj.has_previous():
            r['previous'] = page_obj.previous_page_number()
            r['has_previous'] = True
        else:
            r['has_previous'] = False

        if page_obj.has_next():
            r['next'] = page_obj.next_page_number()
            r['has_next'] = True
        else:
            r['has_next'] = False

        if hasattr(page, "search_data"):
            r['search_data']=page.search_data
        if hasattr(page, "search_task"):
                r['search_task']=page.search_task
        if hasattr(page, "search_method"):
                r['search_method']=page.search_method
        if hasattr(page, "search_challenge"):
                r['search_challenge']=page.search_challenge

        if context.has_key('searchterm'):
            r['searchterm']=quote(context['searchterm'],'')
            if context.has_key('klass'):
                r['klass']=quote(context['klass'],'')
        if context.has_key('selecttab'):
            r['selecttab']=context['selecttab']

        return r
