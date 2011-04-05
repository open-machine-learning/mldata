# -*- coding: utf-8 -*-
# Copyright 2007, 2008,2009 by Benoît Chesneau <benoitc@e-engura.org>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

# views
from django.contrib.auth import views as auth_views
from django_authopenid import views as oid_views
from registration import views as reg_views

extra_context = {
    'section': 'accounts',
}

urlpatterns = patterns('',
    # django registration activate
    url(r'^activate/(?P<activation_key>\w+)/$', reg_views.activate,
        {'template_name': 'registration/activated.html',
        'extra_context': extra_context },
        name='registration_activate'
    ),

    # user profile
    url(r'^password/reset/$', auth_views.password_reset,
        {'template_name': 'registration/pw_reset.html',
         'email_template_name' : 'registration/pw_reset_email.html'},
        name='auth_password_reset'),
    url(r'^password/reset/confirm/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm,
        {'template_name': 'registration/pw_reset_confirm.html'},
        name='auth_password_reset_confirm'),
    url(r'^password/reset/complete/$',
        auth_views.password_reset_complete,
        {'template_name': 'registration/pw_reset_complete_openid.html'},
        name='auth_password_reset_complete'),
    url(r'^password/reset/done/$',
        auth_views.password_reset_done,
        {'template_name': 'registration/pw_reset.html'},
        name='auth_password_reset_done'),
    url(r'^password/$',oid_views.password_change, name='auth_password_change'),

    # manage account registration
    url(r'^associate/complete/$', oid_views.complete_associate, name='user_complete_associate'),
    url(r'^associate/$', oid_views.associate, name='user_associate'),
    url(r'^dissociate/$', oid_views.dissociate, name='user_dissociate'),
    url(r'^register/$', oid_views.register, name='user_register'),
    url(r'^signout/$', oid_views.signout,
        {'template_name': 'registration/signed_out.html'},
        name='user_signout',
    ),
    url(r'^signin/complete/$', oid_views.complete_signin, name='user_complete_signin'),
    url(r'^signin/$', oid_views.signin, name='user_signin'),
    url(r'^signup/$', reg_views.register, 
        {'template_name': 'registration/signup.html',
        'extra_context': extra_context},
        name='registration_register'),
    url(r'^signup/complete/$',direct_to_template, 
        {'template': 'registration/activation_sent.html',
        'extra_context': extra_context},
        name='registration_complete'
    ),

    # yadis uri
    url(r'^yadis.xrdf$', oid_views.xrdf, name='oid_xrdf'),
)
