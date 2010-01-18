from django.views.generic.list_detail import object_list
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseForbidden
from django_authopenid.models import UserAssociation
from openid.consumer import consumer

import re

attrs_dict = { 'class': 'required' }
username_re = re.compile(r'^\w+$')

class ChangeUserDetailsForm(forms.Form):
    """
    Form for registering a new user account.

    Validates that the password is entered twice and matches,
    and that the username is not already taken.

    """
    firstname = forms.CharField(max_length=30,
            widget=forms.TextInput(attrs=attrs_dict),
            label=u'First Name', required=False)
    lastname = forms.CharField(max_length=30,
            widget=forms.TextInput(attrs=attrs_dict),
            label=u'Last Name', required=False)
    email = forms.EmailField(widget=forms.TextInput(attrs=dict(attrs_dict,
        max_length=200)),
        label=u'Email address')
    openid_url = forms.CharField(max_length=255,
            widget=forms.TextInput(attrs=attrs_dict),
            label=u'OpenID URL', required=False)
    password1 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict),
            label=u'Password', required=False)
    password2 = forms.CharField(widget=forms.PasswordInput(attrs=attrs_dict),
            label=u'Password (again, to catch typos)', required=False)

    def clean_firstname(self):
        """
        Validates that the first is alphanumeric
        """
        if 'firstname' in self.cleaned_data:
            if self.cleaned_data['firstname'] and not username_re.search(self.cleaned_data['firstname']):
                raise forms.ValidationError(u'First name can only contain letters, numbers and underscores')
        return self.cleaned_data['firstname']

    def clean_lastname(self):
        """
        Validates that the lastname is alphanumeric
        """
        if 'firstname' in self.cleaned_data:
            if self.cleaned_data['lastname'] and not username_re.search(self.cleaned_data['lastname']):
                raise forms.ValidationError(u'Last name can only contain letters, numbers and underscores')
        return self.cleaned_data['lastname']

    def clean_username(self):
        """
        Validates that the username is alphanumeric and is not already
        in use.

        """
        if 'username' in self.cleaned_data:
            if not username_re.search(self.cleaned_data['username']):
                raise forms.ValidationError(u'Usernames can only contain letters, numbers and underscores')
            try:
                user = User.objects.get(username__exact=self.cleaned_data['username'])
            except User.DoesNotExist:
                return self.cleaned_data['username']
            raise forms.ValidationError(u'This username is already taken. Please choose another.')


    def clean_openid_url(self):
        """
        Validates that OpenID URL starts with 'http' and verifies that given
        ID exists.
        """
        item = self.cleaned_data['openid_url']
        if item:
            if not item.startswith('http'):
                raise forms.ValidationError(u'OpenID URL must start with "http"')

            # access OpenID provider to get verified identity_url
            # this looks winged...
            c = consumer.Consumer({}, None)
            try:
                c.begin(item)
                r = c.complete({}, item)
                item = r.identity_url
            except consumer.DiscoveryFailure, e:
                raise forms.ValidationError(e)

        return item



    def clean_password1(self):
        """
        Validates that a password is given if no OpenID URL is supplied.
        """
        if 'password1' in self.cleaned_data:
            item = self.cleaned_data['password1']
        else:
            item = None

        if not self.cleaned_data['openid_url'] and not item:
            raise forms.ValidationError(u'You must use a password when not supplying an OpenID URL')

        return item


    def clean_password2(self):
        """
        Validates that the two password inputs match.

        """
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data and \
                self.cleaned_data['password1'] == self.cleaned_data['password2']:
                    return self.cleaned_data['password2']
        raise forms.ValidationError(u'You must type the same password each time')

    def save(self, u):
        u.first_name=self.cleaned_data['firstname']
        u.last_name=self.cleaned_data['lastname']
        u.email=self.cleaned_data['email']
        u.set_password(self.cleaned_data['password1'])
        u.save()

        # for some strange reason (primary key == openid_url != int?), a new
        # item is created when saving an existing one, so delete the old
        try:
            UserAssociation.objects.get(user=u).delete()
        except UserAssociation.DoesNotExist:
            pass
        finally:
            ua = UserAssociation(
                openid_url=self.cleaned_data['openid_url'],
                user=u
            )
            ua.save()


def show_user_list(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    return object_list(request,
            paginate_by=10,
            queryset=User.objects.all(),
            template_name='user/user_list.html')


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
        { 'object': entry, 'form' : form },
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
        'password1': entry.password,
        'password2': entry.password,
    })

    if request.method == 'POST':
        form = ChangeUserDetailsForm(request.POST)
        if form.is_valid():
            form.save(entry)
            return render_to_response(
                'user/user_change_done.html',
                { 'object': entry, },
                context_instance=RequestContext(request)
            )

    return render_to_response(
        'user/user_detail.html',
        { 'object': entry, 'form' : form, },
        context_instance=RequestContext(request)
    )
