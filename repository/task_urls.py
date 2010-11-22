"""
URL patterns for Repository
"""

from django.conf.urls.defaults import *
import repository.views as views
import repository.views.task
from repository.models.data import Data

urlpatterns = patterns('',
    url(r'^$', views.task.index, name='task_index'),
    url(r'^by_pub_date/$', views.task.index, {'order_by' : '-pub_date'}, name='task_index_by_pub_date'),
    url(r'^by_name/$', views.task.index, {'order_by' : 'name'}, name='task_index_by_name'),
    url(r'^by_rating/$', views.task.index, {'order_by' : '-rating_avg'}, name='task_index_by_rating'),
    url(r'^by_submitter/$', views.task.index, {'order_by' : 'user__username'}, name='task_index_by_submitter'),
    url(r'^by_downloads/$', views.task.index, {'order_by' : '-downloads'}, name='task_index_by_downloads'),
    url(r'^by_views/$', views.task.index, {'order_by' : '-hits'}, name='task_index_by_views'),
    url(r'^my/$', views.task.my, name='task_my'),
    url(r'^new/$', views.task.new, name='task_new'),
    url(r'^new_from_data/(?P<cur_data>[A-Za-z0-9-_]+)/$', views.task.new_from_data, name='task_new_from_data'),
    url(r'^view/(?P<id>\d+)/$', views.task.view, name='task_view'),
    url(r'^viewslug/(?P<slug_task>[A-Za-z0-9-_]+)/$', views.task.view_slug, name='task_view_slug'),
    url(r'^viewslug/(?P<slug_task>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.task.view_slug, name='task_view_slug_ver'),

    url(r'^task_binclass/$', views.task.index, {'filter_type' : 'Binary Classification'}, name='task_binclass'),
    url(r'^task_multiclass/$', views.task.index, {'filter_type' : 'Multi Class Classification'}, name='task_multiclass'),
    url(r'^task_regression/$', views.task.index, {'filter_type' : 'Regression'}, name='task_regression'),

    url(r'^edit/(?P<id>\d+)/$', views.task.edit, name='task_edit'),
    url(r'^delete/(?P<id>\d+)/$', views.task.delete, name='task_delete'),
    url(r'^activate/(?P<id>\d+)/$', views.task.activate, name='task_activate'),
    url(r'^fork/(?P<id>\d+)/$', views.task.fork, name='task_fork'),
    url(r'^rate/(?P<id>\d+)/$', views.task.rate, name='repository_task_rate'),
    url(r'^download/(?P<slug>[A-Za-z0-9-_]+)/$', views.task.download, name='task_download'),
    url(r'^download/xml/([A-Za-z0-9-_]+)/$', views.task.download_xml, name='task_download_xml'),
    url(r'^download/matlab/([A-Za-z0-9-_]+)/$', views.task.download_matlab, name='task_download_matlab'),
    url(r'^download/octave/([A-Za-z0-9-_]+)/$', views.task.download_octave, name='task_download_octave'),
    #(r'^predict/(?P<slug>[A-Za-z0-9-_]+)/$', views.task.predict, name='task_predict'),
    url(r'^measures/list/(?P<type>[A-Za-z0-9-_ ]+)/$', views.task.get_measures, name='task_measure_list'),
    url(r'^measures/help/(?P<type>[A-Za-z0-9-_ ]+)/(?P<name>[A-Za-z0-9-_ ]+)/$', views.task.get_measure_help, name='task_measure_help'),
)
