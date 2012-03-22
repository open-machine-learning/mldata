"""
Admin classes in app Repository - kind of unused at the moment
"""

from django.contrib import admin
from django.forms import TextInput
from repository.models import *


class DataAdmin(admin.ModelAdmin):
    """Admin class for Data"""
    list_display = ('name', 'version', 'pub_date', 'slug', 'user', 'is_public', 'is_current', 'file', 'format')
    date_hierarchy = 'pub_date'
    list_filter =['pub_date', 'user', 'is_public', 'is_current', 'tags', 'format']
    search_fields = ['name','file']
    formfield_overrides = {
        models.FileField: {'widget': TextInput}
    }

    def rename_file(self, request, queryset):
        """Move the file"""
        old_name = request.file.name
        new_name = "dummy"
        #file_move_save(old_name, new_name, allow_overwrite=False)
        self.message_user(request, "Moved file from %s to %s"
                          % (old_name, new_name))
    rename_file.short_description = "Move the data file (one item only)"
admin.site.register(Data, DataAdmin)




class SlugAdmin(admin.ModelAdmin):
    """Admin class for Slug"""
    list_display = ('text',)
admin.site.register(Slug, SlugAdmin)

class MethodAdmin(admin.ModelAdmin):
    """Admin class for Method"""
    list_display = ('name', 'version', 'pub_date', 'slug', 'is_public', 'is_current')
    date_hierarchy = 'pub_date'
    list_filter =['pub_date', 'user', 'is_public', 'is_current', 'tags']
    search_fields = ['name']
admin.site.register(Method, MethodAdmin)

class ResultAdmin(admin.ModelAdmin):
    """Admin class for Result"""
    list_display = ('method', 'task', 'challenge', 'aggregation_score', 'pub_date',)
    date_hierarchy = 'pub_date'
    list_filter =['method', 'task', 'challenge']
    search_fields = ['name']
admin.site.register(Result, ResultAdmin)

class TaskAdmin(admin.ModelAdmin):
    """Admin class for Task"""
    list_display = ('name', 'version', 'pub_date', 'slug', 'is_public', 'is_current')
    date_hierarchy = 'pub_date'
    list_filter =['pub_date', 'user', 'is_public', 'is_current', 'tags']
    search_fields = ['name']
admin.site.register(Task, TaskAdmin)

class ChallengeAdmin(admin.ModelAdmin):
    """Admin class for Challenge"""
    list_display = ('name', 'version', 'pub_date', 'slug', 'is_public', 'is_current')
    date_hierarchy = 'pub_date'
    list_filter =['pub_date', 'user', 'is_public', 'is_current', 'tags']
    search_fields = ['name']
admin.site.register(Challenge, ChallengeAdmin)

class LicenseAdmin(admin.ModelAdmin):
    """Admin class for Challenge"""
    list_display = ('name', 'url')
    list_filter =['name', 'url']
    search_fields = ['name']
admin.site.register(License, LicenseAdmin)
