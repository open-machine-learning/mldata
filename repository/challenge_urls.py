"""
URL patterns for Repository
"""

from django.conf.urls.defaults import *
import repository.views as views
import repository.views.challenge

urlpatterns = patterns('',
    url(r'^$', views.challenge.index, name='challenge_index'),
    url(r'^by_pub_date/$', views.challenge.index, {'order_by' : '-pub_date'}, name='challenge_index_by_pub_date'),
    url(r'^by_name/$', views.challenge.index, {'order_by' : 'name'}, name='challenge_index_by_name'),
    url(r'^by_rating/$', views.challenge.index, {'order_by' : '-rating_avg'}, name='challenge_index_by_rating'),
    url(r'^by_submitter/$', views.challenge.index, {'order_by' : 'user'}, name='challenge_index_by_submitter'),
    url(r'^by_downloads/$', views.challenge.index, {'order_by' : '-downloads'}, name='challenge_index_by_downloads'),
    url(r'^by_views/$', views.challenge.index, {'order_by' : '-hits'}, name='challenge_index_by_views'),
    (r'^my/$', views.challenge.my),
    (r'^view/(?P<id>\d+)/$', views.challenge.view),
    (r'^viewslug/(?P<slug_challenge>[A-Za-z0-9-_]+)/$', views.challenge.view_slug),
    (r'^viewslug/(?P<slug_challenge>[A-Za-z0-9-_]+)/(?P<version>\d+)/$', views.challenge.view_slug),
    (r'^new/$', views.challenge.new),
    (r'^edit/(?P<id>\d+)/$', views.challenge.edit),
    (r'^delete/(?P<id>\d+)/$', views.challenge.delete),
    (r'^activate/(?P<id>\d+)/$', views.challenge.activate),
    url(r'^rate/(?P<id>\d+)/$', views.challenge.rate, name='repository_challenge_rate'),
    (r'^score/download/(?P<id>\d+)/$', views.challenge.score_download),
    (r'^tasks/(?P<id>\d+)/$', views.challenge.get_tasks),
)
