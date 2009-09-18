from django.contrib import admin
from about.models import About

class AboutAdmin(admin.ModelAdmin):
    pass

admin.site.register(About, AboutAdmin)
