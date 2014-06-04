"""
URLconf for app Blog
"""

from django.conf.urls import *
from django.views.generic.dates import ArchiveIndexView
from blog.models import Post
from blog.feeds import RssBlogFeed
import blog.views

info_dict = {
    'queryset' : Post.objects.all(),
    'date_field' : 'pub_date',
    'extra_context': {
        'section': 'blog',
    }
}

urlpatterns = patterns('',
                       url(r'^$',
                           ArchiveIndexView.as_view(model=Post, date_field="pub_date"),
                           name='blog_index'),
                       url(r'^new/$', blog.views.new),
                       url(r'^archive/$',
                           ArchiveIndexView.as_view(model=Post, date_field="pub_date"),
                           name='blog_archive'),
                       url(r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\w{1,2})/(?P<slug>[A-Za-z0-9-_]+)/$',
                           'DateDetailView',
                           dict(info_dict, slug_field='slug', month_format='%m')),
                       (r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\w{1,2})/$', 'DayArchiveView', dict(info_dict, month_format='%m')),
                       (r'^(?P<year>\d{4})/(?P<month>\d{2})/$', 'MonthArchiveView', dict(info_dict, month_format='%m')),
                       (r'^(?P<year>\d{4})/$', 'YearArchiveView', info_dict),
                       (r'^rss/latest/$', RssBlogFeed),
)
