"""
Sitemaps for app Forum
"""

from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse
from forum.models import Forum, Thread, Post



class ForumSitemap(Sitemap):
    """Sitemap for Forum."""
    changefreq = 'weekly'

    def items(self):
        return Forum.objects.all()

    def last_mod(self, obj):
        return obj._get_forum_latest_post.time



class ThreadSitemap(Sitemap):
    """Sitemap for Thread."""
    changefreq = 'daily'

    def items(self):
        return Thread.objects.all()

    def last_mod(self, obj):
        return obj.latest_post_time



class PostSitemap(Sitemap):
    """Sitemap for Post."""
    changefreq = 'weekly'

    def items(self):
        return Post.objects.all()

    def last_mod(self, obj):
        return obj.time
