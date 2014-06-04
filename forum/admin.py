"""
Admin class in app Forum
"""

from django.contrib import admin
from forum.models import Forum, Thread, Post, Subscription

class ForumAdmin(admin.ModelAdmin):
    """Admin class for forums."""
    list_display = ('title', '_parents_repr')
    list_filter = ('groups',)
    ordering = ['ordering', 'parent', 'title']
    prepopulated_fields = {"slug": ("title",)}
admin.site.register(Forum, ForumAdmin)

class SubscriptionAdmin(admin.ModelAdmin):
    """Admin class for subscriptions - unused atm."""
    list_display = ['author','thread']
admin.site.register(Subscription, SubscriptionAdmin)

class ThreadAdmin(admin.ModelAdmin):
    """Admin class for threads."""
    list_display = ('title', 'forum', 'latest_post_time')
    list_filter = ('forum',)
admin.site.register(Thread, ThreadAdmin)

admin.site.register(Post)
