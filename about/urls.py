"""
URLconf for app About
"""

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template

extra_context = { 'section': 'about' }

urlpatterns = patterns('',
    url(r'^$', direct_to_template,
        {'template':'about/motivation.html', 'extra_context':extra_context},
        name='about_index'),
    url(r'^license/$', direct_to_template, {
        'template':'about/license.html', 'extra_context':extra_context},
        name='about_license'),
    url(r'^hdf5/$', direct_to_template, {
        'template':'about/hdf5.html', 'extra_context':extra_context},
       name='about_hdf5'),
    url(r'^related/$', direct_to_template,
        {'template':'about/related.html', 'extra_context':extra_context},
        name='about_related'),
    url(r'^impressum/$', direct_to_template,
        {'template':'about/impressum.html', 'extra_context':extra_context},
        name='about_impressum'),
    url(r'^tos/$', direct_to_template,
        {'template':'about/tos.html', 'extra_context':extra_context},
        name='about_tos'),
)
