"""
Implements feeds like RSS or Atom for app Forum
"""

from django.conf import settings
from django.contrib.syndication.feeds import Feed
from django.contrib.syndication.feeds import FeedDoesNotExist
from django.utils.feedgenerator import Atom1Feed
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _

from forum.models import Forum, Thread, Post

class RssForumFeed(Feed):
    """RSS feed for forum.

    @cvar title_template: template filename for post title
    @type title_template: string
    @cvar description_template: template filename for post description
    @type description_template: string
    """
    title_template = 'forum/feeds/post_title.html'
    description_template = 'forum/feeds/post_description.html'

    def get_object(self, bits):
        """Get a forum object.

        @param bits: bits of the item's slug
        @type bits: list
        @return: a forum item matching exactly the slug or none
        @rtype: Forum
        """
        if len(bits) == 0:
            return None
        else:
            slug = "/".join(bits)
            return Forum.objects.get(slug__exact=slug)

    def title(self, obj):
        """Get the title for the given object.

        @param obj: object to get the title for
        @type obj: Forum
        @return: object's or generic title
        @rtype: string
        """
        if not hasattr(self, '_site'):
            self._site = Site.objects.get_current()

        if obj:
            return _("%(title)s's Forum: %(forum)s") % { 
                'title': self._site.name,
                'forum': obj.title }
        else:
            return _("%(title)s's Forum") % {'title': self._site.name}

    def description(self, obj):
        """Get the object's description.

        @param obj: object to get description for
        @type obj: Forum
        @return: object's or generic description
        @rtype: string
        """
        if obj:
            return obj.description
        else:
            return _('Latest forum posts')

    def link(self, obj):
        """Get object's URL.

        @param obj: object to get URL for
        @type obj: Forum
        @return: object's or forum's index URL
        @rtype: string
        """
        if obj:
            return obj.get_absolute_url()
        else:
            return reverse('forum_index')

    def get_query_set(self, obj):
        """Get other posts from object's forum, ordered descending by time.

        @param obj: object to get posts for
        @type obj: Post
        @return: a queryset with thread's or all posts
        @rtype: Django queryset
        """
        if obj:
            return Post.objects.filter(thread__forum__pk=obj.id).order_by('-time')
        else:
            return Post.objects.order_by('-time')

    def items(self, obj):
        """Get last 15 items of object's related posts.

        @param obj: post ot get related for
        @type obj: Post
        @return a list of the last 15 related posts
        @rtype: list
        """
        return self.get_query_set(obj)[:15]

    def item_pubdate(self, item):
        """Get publication date of given item.

        @param item: item to get publication date for
        @type item: Post
        @return: publication date
        @rtype: datetime
        """
        return item.time


class AtomForumFeed(RssForumFeed):
    """Atom feed for forum.

    @cvar feed_type: type of feed -> Atom
    @type feed_type: Atom1Feed
    """
    feed_type = Atom1Feed

    def subtitle(self, obj):
        """Get subtitle for feed.

        @param obj: object to get subtitle for
        @type obj: Post
        @return: a subtitle
        @rtype: string
        """
        return RssForumFeed.description(self, obj)
