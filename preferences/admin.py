"""
Admin classes for app Preferences
"""

from django.contrib import admin
from preferences.models import Preferences

class PreferencesAdmin(admin.ModelAdmin):
    """Admin class for preferences."""
    pass
admin.site.register(Preferences, PreferencesAdmin)
