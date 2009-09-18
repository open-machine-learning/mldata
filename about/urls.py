from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'about.views.index'),
    (r'^impressum/$', 'about.views.impressum'),
)
