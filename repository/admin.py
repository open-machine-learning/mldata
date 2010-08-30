"""
Admin classes in app Repository - kind of unused at the moment
"""

from django.contrib import admin
from repository.models import *

class SlugAdmin(admin.ModelAdmin):
    """Admin class for Solution"""
    list_display = ('text',)
admin.site.register(Slug, SlugAdmin)

