from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'about.views.index'),
    (r'^about/$', 'about.views.index'),
    (r'^impressum/$', 'about.views.impressum'),
    (r'^tos/$', 'about.views.tos'),
)
