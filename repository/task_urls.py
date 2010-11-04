"""
URL patterns for Repository
"""

from django.conf.urls.defaults import *
import repository.views as views
import repository.views.task

urlpatterns = patterns('',
    url(r'^$', views.task.index, name='task_index'),
    url(r'^by_pub_date/$', views.task.index, {'order_by' : '-pub_date'}, name='task_index_by_pub_date'),
    url(r'^by_name/$', views.task.index, {'order_by' : 'name'}, name='task_index_by_name'),
    url(r'^by_rating/$', views.task.index, {'order_by' : '-rating_avg'}, name='task_index_by_rating'),
    url(r'^by_submitter/$', views.task.index, {'order_by' : 'user'}, name='task_index_by_submitter'),
    url(r'^by_downloads/$', views.task.index, {'order_by' : '-downloads'}, name='task_index_by_downloads'),
    url(r'^by_views/$', views.task.index, {'order_by' : '-hits'}, name='task_index_by_views'),
    (r'^my/$', views.task.my),
    (r'^new/$', views.task.new),
    (r'^view/(?P<id>\d+)/$', views.task.view),
    (r'^viewslug/(?P<slug_task>[A-Za-z0-9-_]+)/$', views.task.view_slug),
    (r'^viewslug/(?P<slug_task>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.task.view_slug),

    (r'^edit/(?P<id>\d+)/$', views.task.edit),
    (r'^delete/(?P<id>\d+)/$', views.task.delete),
    (r'^activate/(?P<id>\d+)/$', views.task.activate),
    url(r'^rate/(?P<id>\d+)/$', views.task.rate, name='repository_task_rate'),
    (r'^download/(?P<slug>[A-Za-z0-9-_]+)/$', views.task.download),
    #(r'^predict/(?P<slug>[A-Za-z0-9-_]+)/$', views.task.predict),
    (r'^measures/list/(?P<type>[A-Za-z0-9-_ ]+)/$', views.task.get_measures),
    (r'^measures/help/(?P<type>[A-Za-z0-9-_ ]+)/(?P<name>[A-Za-z0-9-_ ]+)/$', views.task.get_measure_help),
)
