"""
Model classes for app Blog
"""

from django.db import models
from django.forms import ModelForm
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from utils import slugify


class Post(models.Model):
    """A Blog post.

    @cvar pub_date: post's publication date
    @type pub_date: datetime / models.DateTimeField
    @cvar slug: post's slug
    @type slug: string / models.SlugField
    @cvar headline: post's headline
    @type headline: string / models.CharField
    @cvar summary: post's summary
    @type summary: string / models.CharField
    @cvar body: post's body
    @type body: string / models.TextField
    @cvar author: post's author
    @type author: Django user / models.ForeignKey
    """
    pub_date = models.DateTimeField()
    slug = models.SlugField(unique_for_date='pub_date', editable=False)
    headline = models.CharField(max_length=200)
    summary = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    author = models.ForeignKey(User)


    class Meta:
        ordering = ('-pub_date',)
        get_latest_by = 'pub_date'


    def __unicode__(self):
        return unicode(self.headline)


    def get_absolute_url(self):
        return reverse('blog_index') + "%s/%s/" % (self.pub_date.strftime("%Y/%m/%d").lower(), self.slug)


    def get_comment_url(self):
        return self.get_absolute_url() + "#comments"


    def save(self):
        if not self.id:
            self.slug = slugify(self.headline)
        super(Post, self).save()



class PostForm(ModelForm):
    """Form class for model Post."""

    class Meta:
        model = Post
        exclude = ('pub_date', 'slug', 'author',)
