from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'hello.views.index'),
    (r'^foo/$', 'hello.views.index'),
)
