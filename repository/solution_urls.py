"""
URL patterns for Repository
"""

from django.conf.urls.defaults import *
import repository.views as views
import repository.views.solution

urlpatterns = patterns('',
    url(r'^$', views.solution.index, name='solution_index'),
    url(r'^by_pub_date/$', views.solution.index, {'order_by' : '-pub_date'}, name='solution_index_by_pub_date'),
    url(r'^by_name/$', views.solution.index, {'order_by' : 'name'}, name='solution_index_by_name'),
    url(r'^by_rating/$', views.solution.index, {'order_by' : '-rating_avg'}, name='solution_index_by_rating'),
    url(r'^by_submitter/$', views.solution.index, {'order_by' : 'user'}, name='solution_index_by_submitter'),
    url(r'^by_downloads/$', views.solution.index, {'order_by' : '-downloads'}, name='solution_index_by_downloads'),
    url(r'^by_views/$', views.solution.index, {'order_by' : '-hits'}, name='solution_index_by_views'),
    (r'^my/$', views.solution.my),
    (r'^view/(?P<id>\d+)/$', views.solution.view),
    url(r'^viewslug/(?P<slug_solution>[A-Za-z0-9-_]+)/$', views.solution.view_slug),
    (r'^viewslug/(?P<slug_solution>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.solution.view_slug),
    (r'^new/$', views.solution.new),
    (r'^edit/(?P<id>\d+)/$', views.solution.edit),
    (r'^delete/(?P<id>\d+)/$', views.solution.delete),
    (r'^activate/(?P<id>\d+)/$', views.solution.activate),
    url(r'^rate/(?P<id>\d+)/$', views.solution.rate, name='repository_solution_rate'),
    (r'^score/download/(?P<id>\d+)/$', views.solution.score_download),
    (r'^result/(?P<id>\d+)/(?P<resolution>[a-z]+)/$', views.solution.plot_single_curve),
    (r'^results/(?P<id>\d+)/(?P<resolution>[a-z]+)/$', views.solution.plot_multiple_curves),
)
