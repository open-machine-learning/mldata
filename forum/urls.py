"""
URLConf for app Forum
"""

from django.conf.urls import *
from forum.models import Forum
from forum.feeds import RssForumFeed, AtomForumFeed
from forum.sitemap import ForumSitemap, ThreadSitemap, PostSitemap
from forum.views import ForumView, ForumListView, ThreadView

feed_dict = {
    'rss' : RssForumFeed,
    'atom': AtomForumFeed
}

sitemap_dict = {
    'forums': ForumSitemap,
    'threads': ThreadSitemap,
    'posts': PostSitemap,
}

urlpatterns = patterns('',
                       url(r'^$', ForumListView.as_view(), name='forum_index'),
#                       url(r'^(?P<url>(rss|atom).*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feed_dict}),
url('^(?P<url>(rss|atom).*)/$', RssForumFeed()),

    url(r'^thread/(?P<thread>[0-9]+)/$', ThreadView.as_view(), name='forum_view_thread'),
    url(r'^thread/(?P<thread>[0-9]+)/reply/$', 'forum.views.reply', name='forum_reply_thread'),

    url(r'^subscriptions/$', 'forum.views.updatesubs', name='forum_subscriptions'),

    url(r'^(?P<slug>[-\w]+)/$', ForumView.as_view(), name='forum_thread_list'),
    url(r'^(?P<forum>[-\w]+)/new/$', 'forum.views.newthread', name='forum_new_thread'),

    url(r'^([-\w/]+/)(?P<forum>[-\w]+)/new/$', 'forum.views.newthread'),
    url(r'^([-\w/]+/)(?P<slug>[-\w]+)/$', ForumView.as_view(), name='forum_thread_list'),

    (r'^sitemap.xml$', 'django.contrib.sitemaps.views.index', {'sitemaps': sitemap_dict}),
    (r'^sitemap-(?P<section>.+)\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemap_dict}),
)
