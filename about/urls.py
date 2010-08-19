"""
URLconf for app About
"""

from django.conf.urls.defaults import *
from django.views.generic.simple import direct_to_template
from settings import MEDIA_URL
import ml2h5.converter

extra_context = {
    'section': 'about',
    'MEDIA_URL': MEDIA_URL,
    'supported_formats': {
        'to': ml2h5.converter.TO_H5,
        'from': ml2h5.converter.FROM_H5,
    },
}

urlpatterns = patterns('',
    url(r'^$', direct_to_template,
        {'template':'about/index.html', 'extra_context':extra_context},
        name='about_index'),
    url(r'^motivation/$', direct_to_template, {
        'template':'about/motivation.html', 'extra_context':extra_context},
        name='about_motivation'),
    url(r'^license/$', direct_to_template, {
        'template':'about/license.html', 'extra_context':extra_context},
        name='about_license'),
    url(r'^hdf5/$', direct_to_template, {
        'template':'about/hdf5.html', 'extra_context':extra_context},
       name='about_hdf5'),
    url(r'^hdf5/example/$', direct_to_template, {
        'template':'about/hdf5_example.html', 'extra_context':extra_context},
       name='about_hdf5_example'),
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
