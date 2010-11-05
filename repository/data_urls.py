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
    (r'^my/$', views.data.my),
    (r'^new/$', views.data.new),
    (r'^new/review/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.new_review),
    (r'^view/(?P<id>\d+)/$', views.data.view),
    url(r'^viewslug/(?P<slug>[A-Za-z0-9-_]+)/$', views.data.view_slug),
    (r'^viewslug/(?P<slug>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.data.view_slug),

    (r'^edit/(?P<id>\d+)/$', views.data.edit),
    (r'^delete/(?P<id>\d+)/$', views.data.delete),
    (r'^activate/(?P<id>\d+)/$', views.data.activate),
    (r'^download/([A-Za-z0-9-_]+)/$', views.data.download),
    (r'^download/xml/([A-Za-z0-9-_]+)/$', views.data.download_xml),
    (r'^download/csv/([A-Za-z0-9-_]+)/$', views.data.download_csv),
    (r'^download/arff/([A-Za-z0-9-_]+)/$', views.data.download_arff),
    (r'^download/libsvm/([A-Za-z0-9-_]+)/$', views.data.download_libsvm),
    (r'^download/matlab/([A-Za-z0-9-_]+)/$', views.data.download_matlab),
    (r'^download/octave/([A-Za-z0-9-_]+)/$', views.data.download_octave),
    url(r'^rate/(?P<id>\d+)/$', views.data.rate, name='repository_data_rate'),
)
