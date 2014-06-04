"""
Form classes used in app Forum
"""

from django import forms
from django.utils.translation import ugettext as _

class CreateThreadForm(forms.Form):
    """Form to create threads.

    @cvar title: title of Thread
    @type title: forms.CharField
    @cvar body: body of Thread
    @type body: forms.CharField
    @cvar subscribe: if thread can be subscribed to
    @type subscribe: forms.BooleanField
    """
    title = forms.CharField(label=_("Title"), max_length=100)
    body = forms.CharField(label=_("Body"), widget=forms.Textarea(attrs={'rows':8, 'cols':50}))
    subscribe = forms.BooleanField(label=_("Subscribe via email"), required=False)

class ReplyForm(forms.Form):
    """Form to reply to a thread

    @cvar body: body of Reply
    @type body: forms.CharField
    @cvar subscribe: if reply can be subscribed to
    @type subscribe: forms.BooleanField
    """
    body = forms.CharField(label=_("Body"), widget=forms.Textarea(attrs={'rows':8, 'cols':50}))
    subscribe = forms.BooleanField(label=_("Subscribe via email"), required=False)

