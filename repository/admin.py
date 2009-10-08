from django.contrib import admin
from repository.models import Data, Task, Solution, Split

class DataAdmin(admin.ModelAdmin):
    list_display = ('pub_date', 'slug', 'is_public')
admin.site.register(Data, DataAdmin)

class TaskAdmin(admin.ModelAdmin):
    list_display = ('pub_date', 'slug', 'is_public')
admin.site.register(Task, TaskAdmin)

class SolutionAdmin(admin.ModelAdmin):
    list_display = ('pub_date', 'slug', 'is_public')
admin.site.register(Solution, SolutionAdmin)

class SplitAdmin(admin.ModelAdmin):
    pass
admin.site.register(Split, SplitAdmin)


