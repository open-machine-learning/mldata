"""
Admin classes in app Repository - kind of unused at the moment
"""

from django.contrib import admin
from repository.models import Data, Task, Solution

class DataAdmin(admin.ModelAdmin):
    """Admin class for Data"""
    list_display = ('pub_date', 'slug', 'is_public')
admin.site.register(Data, DataAdmin)

class TaskAdmin(admin.ModelAdmin):
    """Admin class for Task"""
    list_display = ('pub_date', 'slug', 'is_public')
admin.site.register(Task, TaskAdmin)

class SolutionAdmin(admin.ModelAdmin):
    """Admin class for Solution"""
    list_display = ('pub_date', 'slug', 'is_public')
admin.site.register(Solution, SolutionAdmin)

