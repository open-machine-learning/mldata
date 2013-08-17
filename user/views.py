from django.views.generic.list import ListView
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden
from django_authopenid.models import UserAssociation

from user.forms import *



def show_user_list(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()
    return ListView.as_view(request,
            paginate_by=10,
            queryset=User.objects.all(),
            template_name='user/user_list.html',
            extra_context={'section': 'accounts'})



def show_user(request, user_id):
    if not request.user.is_authenticated():
        return HttpResponseForbidden()

    entry = get_object_or_404(User, pk=user_id)
    if not request.user.is_superuser and not entry == request.user:
        return HttpResponseForbidden()

    try:
        entry.openid_url = UserAssociation.objects.get(user=entry).openid_url
    except UserAssociation.DoesNotExist:
        entry.openid_url = ''

    form = ChangeUserDetailsForm(initial={
        'firstname': entry.first_name,
        'lastname': entry.last_name,
        'email': entry.email,
        'openid_url': entry.openid_url,
        'password1': '',
        'password2': '',
    })

    entry.last_login = entry.last_login.__str__().split('.')[0]
    entry.date_joined = entry.date_joined.__str__().split('.')[0]

    return render_to_response(
        'user/user_detail.html',
        { 'object': entry, 'form' : form, 'section': 'accounts'},
        context_instance=RequestContext(request)
    )


def update_user(request, user_id):
    if not request.user.is_authenticated():
        return HttpResponseForbidden()

    entry = get_object_or_404(User, pk=user_id)
    if not request.user.is_superuser and not entry == request.user:
        return HttpResponseForbidden()

    try:
        entry.openid_url = UserAssociation.objects.get(user=entry).openid_url
    except UserAssociation.DoesNotExist:
        entry.openid_url = ''

    form = ChangeUserDetailsForm(initial={
        'firstname': entry.first_name,
        'lastname': entry.last_name,
        'email': entry.email,
        'openid_url': entry.openid_url,
        'password1': '',
        'password2': '',
    })

    if request.method == 'POST':
        form = ChangeUserDetailsForm(request.POST)
        if form.is_valid():
            form.save(entry)
            return render_to_response(
                'user/user_change_done.html',
                { 'object': entry, 'section': 'accounts'},
                context_instance=RequestContext(request)
            )

    return render_to_response(
        'user/user_detail.html',
        { 'object': entry, 'form' : form, 'section': 'accounts'},
        context_instance=RequestContext(request)
    )
