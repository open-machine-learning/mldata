from django.contrib import admin
from hello.models import Hello

class HelloAdmin(admin.ModelAdmin):
    pass

admin.site.register(Hello, HelloAdmin)
