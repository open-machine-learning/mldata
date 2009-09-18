from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'about.views.index'),
    (r'^foo/$', 'about.views.index'),
)
