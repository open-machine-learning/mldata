"""
URL patterns for Repository
"""

from django.conf.urls.defaults import *
import repository.views as views
import repository.views.method

urlpatterns = patterns('',
    url(r'^$', views.method.index, name='method_index'),
    url(r'^by_pub_date/$', views.method.index, {'order_by' : '-pub_date'}, name='method_index_by_pub_date'),
    url(r'^by_name/$', views.method.index, {'order_by' : 'name'}, name='method_index_by_name'),
    url(r'^by_rating/$', views.method.index, {'order_by' : '-rating_avg'}, name='method_index_by_rating'),
    url(r'^by_submitter/$', views.method.index, {'order_by' : 'user__username'}, name='method_index_by_submitter'),
    url(r'^by_downloads/$', views.method.index, {'order_by' : '-downloads'}, name='method_index_by_downloads'),
    url(r'^by_views/$', views.method.index, {'order_by' : '-hits'}, name='method_index_by_views'),
    url(r'^my/$', views.method.my, name='method_my'),
    url(r'^view/(?P<id>\d+)/$', views.method.view, name='method_view'),
    url(r'^viewslug/(?P<slug_method>[A-Za-z0-9-_]+)/$', views.method.view_slug, name='method_view_slug'),
    url(r'^viewslug/(?P<slug_method>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.method.view_slug, name='method_view_slug_ver'),
    url(r'^new/$', views.method.new, name='method_new'),
    url(r'^edit/(?P<id>\d+)/$', views.method.edit, name='method_edit'),
    url(r'^delete/(?P<id>\d+)/$', views.method.delete, name='method_delete'),
    url(r'^activate/(?P<id>\d+)/$', views.method.activate, name='method_activate'),
    url(r'^fork/(?P<id>\d+)/$', views.method.fork, name='method_fork'),
    url(r'^rate/(?P<id>\d+)/$', views.method.rate, name='method_rate'),
    url(r'^score/download/(?P<id>\d+)/$', views.method.score_download, name='method_download'),
    url(r'^result/(?P<id>\d+)/(?P<resolution>[a-z]+)/$', views.method.plot_single_curve, name='method_result_curve'),
    url(r'^results/(?P<id>\d+)/(?P<resolution>[a-z]+)/$', views.method.plot_multiple_curves, name='method_result_curves'),
)
