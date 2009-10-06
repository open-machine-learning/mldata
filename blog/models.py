from django.db import models
from django.contrib.auth.models import User
from utils import slugify

class Post(models.Model):
    pub_date = models.DateTimeField()
    slug = models.SlugField(unique_for_date='pub_date', editable=False)
    headline = models.CharField(max_length=200)
    summary = models.TextField(help_text="Use markdown.")
    body = models.TextField(help_text="Use markdown.")
    author = models.ForeignKey(User)

    class Meta:
        ordering = ('-pub_date',)
        get_latest_by = 'pub_date'

    def __unicode__(self):
        return unicode(self.headline)

    def get_absolute_url(self):
        return "/blog/%s/%s/" % (self.pub_date.strftime("%Y/%m/%d").lower(), self.slug)

    def get_comment_url(self):
        return self.get_absolute_url() + "#comments"

    def save(self):
        if not self.id:
            self.slug = slugify(self.headline)
        super(Post, self).save()
