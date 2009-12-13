from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

urlpatterns = patterns('',
    url(r'^$', direct_to_template, {'template':'about/index.html'}, name='about_index'),
    url(r'^impressum/$', direct_to_template, {'template':'about/impressum.html'}, name='about_impressum'),
    url(r'^tos/$', direct_to_template, {'template':'about/tos.html'}, name='about_tos'),
    url(r'^related/$', direct_to_template, {'template':'about/related.html'}, name='about_related'),
)
