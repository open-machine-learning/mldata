from django.conf.urls.defaults import *
import repository.views as views

urlpatterns = patterns('',
    (r'^$', views.index),
    (r'^data/(?P<path>.*)$', 'django.views.static.serve', {'document_root': 'data'}),
)
