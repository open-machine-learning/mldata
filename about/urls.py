from django.conf.urls.defaults import *
import about.views as views

urlpatterns = patterns('',
    url(r'^$', views.index, name='about_index'),
    (r'^about/$', views.index),
    (r'^impressum/$', views.impressum),
    (r'^tos/$', views.tos),
)
