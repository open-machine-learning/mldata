from django.contrib import admin
from blog.models import Post

class PostAdmin(admin.ModelAdmin):
    list_display = ('pub_date', 'headline', 'author')


admin.site.register(Post, PostAdmin)

