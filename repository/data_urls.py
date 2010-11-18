"""
URL patterns for Repository
"""

from django.conf.urls.defaults import *
import repository.views as views
import repository.views.data

urlpatterns = patterns('',
    # data sets
    url(r'^$', views.data.index, name='data_index'),
    url(r'^by_pub_date/$', views.data.index, {'order_by' : '-pub_date'}, name='data_index_by_pub_date'),
    url(r'^by_name/$', views.data.index, {'order_by' : 'name'}, name='data_index_by_name'),
    url(r'^by_rating/$', views.data.index, {'order_by' : '-rating_avg'}, name='data_index_by_rating'),
    url(r'^by_submitter/$', views.data.index, {'order_by' : 'user__username'}, name='data_index_by_submitter'),
    url(r'^by_downloads/$', views.data.index, {'order_by' : '-downloads'}, name='data_index_by_downloads'),
    url(r'^by_views/$', views.data.index, {'order_by' : '-hits'}, name='data_index_by_views'),
    url(r'^by_instances/$', views.data.index, {'order_by' : '-num_instances'}, name='data_index_by_instances'),
    url(r'^by_attributes/$', views.data.index, {'order_by' : '-num_attributes'}, name='data_index_by_attributes'),
    url(r'^my/$', views.data.my, name='data_my'),
    url(r'^new/$', views.data.new, name='data_new'),
    url(r'^new/review/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.new_review, name='data_review'),
    url(r'^view/(?P<id>\d+)/$', views.data.view, name='data_view'),
    url(r'^viewslug/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.view_slug, name='data_view_slug'),
    url(r'^viewslug/(?P<slug>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.data.view_slug, name='data_view_slug_ver'),
    url(r'^edit/(?P<id>\d+)/$', views.data.edit, name='data_edit'),
    url(r'^delete/(?P<id>\d+)/$', views.data.delete, name='data_delete'),
    url(r'^activate/(?P<id>\d+)/$', views.data.activate, name='data_activate'),
    url(r'^download/([A-Za-z0-9-_]+)/$', views.data.download, name='data_download'),
    url(r'^download/xml/([A-Za-z0-9-_]+)/$', views.data.download_xml, name='data_download_xml'),
    url(r'^download/csv/([A-Za-z0-9-_]+)/$', views.data.download_csv, name='data_download_csv'),
    url(r'^download/arff/([A-Za-z0-9-_]+)/$', views.data.download_arff, name='data_download_arff'),
    url(r'^download/libsvm/([A-Za-z0-9-_]+)/$', views.data.download_libsvm, name='data_download_libsvm'),
    url(r'^download/matlab/([A-Za-z0-9-_]+)/$', views.data.download_matlab, name='data_download_matlab'),
    url(r'^download/octave/([A-Za-z0-9-_]+)/$', views.data.download_octave, name='data_download_octave'),
    url(r'^rate/(?P<id>\d+)/$', views.data.rate, name='repository_data_rate'),
)
