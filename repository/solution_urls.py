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
    url(r'^by_submitter/$', views.solution.index, {'order_by' : 'user__username'}, name='solution_index_by_submitter'),
    url(r'^by_downloads/$', views.solution.index, {'order_by' : '-downloads'}, name='solution_index_by_downloads'),
    url(r'^by_views/$', views.solution.index, {'order_by' : '-hits'}, name='solution_index_by_views'),
    url(r'^my/$', views.solution.my, name='solution_my'),
    url(r'^view/(?P<id>\d+)/$', views.solution.view, name='solution_view'),
    url(r'^viewslug/(?P<slug_solution>[A-Za-z0-9-_]+)/$', views.solution.view_slug, name='solution_view_slug'),
    url(r'^viewslug/(?P<slug_solution>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.solution.view_slug, name='solution_view_slug_ver'),
    url(r'^new/$', views.solution.new, name='solution_new'),
    url(r'^edit/(?P<id>\d+)/$', views.solution.edit, name='solution_edit'),
    url(r'^delete/(?P<id>\d+)/$', views.solution.delete, name='solution_delete'),
    url(r'^activate/(?P<id>\d+)/$', views.solution.activate, name='solution_activate'),
    url(r'^fork/(?P<id>\d+)/$', views.solution.fork, name='solution_fork'),
    url(r'^rate/(?P<id>\d+)/$', views.solution.rate, name='repository_solution_rate'),
    url(r'^score/download/(?P<id>\d+)/$', views.solution.score_download, name='solution_download'),
    url(r'^result/(?P<id>\d+)/(?P<resolution>[a-z]+)/$', views.solution.plot_single_curve, name='solution_result_curve'),
    url(r'^results/(?P<id>\d+)/(?P<resolution>[a-z]+)/$', views.solution.plot_multiple_curves, name='solution_result_curves'),
)
