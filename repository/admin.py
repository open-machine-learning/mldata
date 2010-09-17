"""
Admin classes in app Repository - kind of unused at the moment
"""

from django.contrib import admin
from repository.models import *

class DataAdmin(admin.ModelAdmin):
    """Admin class for Data"""
    list_display = ('pub_date', 'slug', 'is_public')
admin.site.register(Data, DataAdmin)

class SlugAdmin(admin.ModelAdmin):
    """Admin class for Slug"""
    list_display = ('text',)
admin.site.register(Slug, SlugAdmin)

class SolutionAdmin(admin.ModelAdmin):
    """Admin class for Solution"""
    list_display = ('pub_date', 'slug', 'is_public',)
admin.site.register(Solution, SolutionAdmin)

class TaskAdmin(admin.ModelAdmin):
    """Admin class for Task"""
    list_display = ('pub_date', 'slug', 'is_public')
admin.site.register(Task, TaskAdmin)

class ChallengeAdmin(admin.ModelAdmin):
    """Admin class for Challenge"""
    list_display = ('pub_date', 'slug', 'is_public')
admin.site.register(Challenge, ChallengeAdmin)
