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

    if context.has_key('page'):
        page=context['page']
        page_obj=page.page_obj
        page_number=page_obj.number
        page_numbers = [n for n in \
                        range(page_number - adjacent_pages, page_number + adjacent_pages + 1) \
                        if n > 0 and n <= page.num_pages]
        results_this_page = page_obj.object_list.count()
        range_base = ((page_number - 1) * page.per_page)
        if len(page_numbers)<=1:
            page_numbers=[]

        r= {
                'hits': page.count,
                'results_per_page': page.per_page,
                'results_this_page': results_this_page,
                'first_this_page': range_base + 1,
                'last_this_page': range_base + results_this_page,
                'page': page_number,
                'pages': page.num_pages,
                'page_numbers': page_numbers,
                'next': page_obj.next_page_number(),
                'previous': page_obj.previous_page_number(),
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'show_first': 1 not in page_numbers,
                'show_last': page.num_pages not in page_numbers,
                }

        if hasattr(page, "search_data"):
            r['search_data']=page.search_data
        if hasattr(page, "search_task"):
                r['search_task']=page.search_task
        if hasattr(page, "search_solution"):
                r['search_solution']=page.search_solution
        if hasattr(page, "search_challenge"):
                r['search_challenge']=page.search_challenge

        if context.has_key('searchterm'):
            r['searchterm']=quote(context['searchterm'],'')
            if context.has_key('klass'):
                r['klass']=quote(context['klass'],'')

        return r
