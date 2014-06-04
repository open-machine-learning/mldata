"""
URLconf for app About
"""

from django.conf.urls import *
from django.views.generic import TemplateView
from settings import MEDIA_URL
from about.views import about_videos
import ml2h5.converter

extra_context = {
    'section': 'about',
    'MEDIA_URL': MEDIA_URL,
    'supported_formats': {
        'to': ml2h5.converter.TO_H5,
        'from': ml2h5.converter.FROM_H5,
    },
}

class AboutView(TemplateView):
    def get_context_data(self, **kwargs):
        context = super(AboutView, self).get_context_data(**kwargs)
        for key in extra_context:
            context[key] = extra_context[key]
        return context

urlpatterns = patterns('',
    url(r'^$',
        AboutView.as_view(template_name = 'about/index.html'),
        name='about_index'),
    url(r'^motivation/$',
        AboutView.as_view(template_name = 'about/motivation.html'),
        name='about_motivation'),
    url(r'^license/$',
        AboutView.as_view(template_name = 'about/license.html'),
        name='about_license'),
    url(r'^hdf5/$',
        AboutView.as_view(template_name = 'about/hdf5.html'),
        name='about_hdf5'),
    url(r'^slicing/$',
        AboutView.as_view(template_name = 'about/slicing.html'),
        name='about_slicing'),
    url(r'^evaluation/$',
        AboutView.as_view(template_name = 'about/evaluation.html'),
        name='about_evaluation'),
    url(r'^hdf5/example/$',
        AboutView.as_view(template_name = 'about/hdf5_example.html'),
        name='about_hdf5_example'),
    url(r'^related/$',
        AboutView.as_view(template_name = 'about/related.html'),
        name='about_related'),
    url(r'^impressum/$',
        AboutView.as_view(template_name = 'about/impressum.html'),
        name='about_impressum'),
    url(r'^tos/$',
        AboutView.as_view(template_name = 'about/tos.html'),
        name='about_tos'),
    url(r'^(?P<video>[A-Za-z0-9-_]+)/$', about_videos,
        {'template':'about/videos.html', 'extra_context':extra_context},
        name='about_videos'),
)
