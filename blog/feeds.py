"""
Implements a blog RSS feed
"""

from blog.wfwfeed import WellFormedWebRss
from blog.models import Post
from django.contrib.sites.models import Site
from django.http import HttpResponse
from utils.markdown import markdown


def RssBlogFeed(request):
    """Get a response page with a feed of the latest 10 blog posts.

    @param request: request data
    @type request: Django request
    @return: a response page including the RSS feed
    @rtype: Django response
    """
    try:
        object_list = Post.objects.all().order_by('-pub_date')[:10]
    except documents.DocumentDoesNotExist:
        raise Http404
    feed = WellFormedWebRss( u"mldata.org's blog",
            "http://mldata.org/blog",
            u'Some thoughts about the machine learning benchmark repository',
            language=u"en")

    for object in object_list:
        link = 'http://%s%s' % (Site.objects.get_current().domain, object.get_absolute_url())
        #commentlink=u'http://%s/software/rss/comments/%i' % (Site.objects.get_current().domain, object.id)
        #comments=commentlink,
        feed.add_item( object.headline.encode('utf-8'),
                link, markdown(object.body),
                author_name=object.author.username.encode('utf-8'),
                pubdate=object.pub_date, unique_id=link)
    response = HttpResponse(mimetype='application/xml')
    feed.write(response, 'utf-8')
    return response
