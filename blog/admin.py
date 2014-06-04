"""
Admin classes for app Blog
"""

from django.contrib import admin
from blog.models import Post

class PostAdmin(admin.ModelAdmin):
    """Admin class for posts."""
    list_display = ('pub_date', 'headline', 'author')
admin.site.register(Post, PostAdmin)
