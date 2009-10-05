"""
All custom blog logic is kept here
"""

import datetime
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from blog.models import BlogItem


def latest(request):
	return render_to_response('blog/latest.html', { 'user': request.user })

def new(request):
	if not request.user.is_authenticated():
		return HttpResponseRedirect(reverse('blog_index'))

	return render_to_response('blog/new.html', { 'user': request.user })


def post(request):
	if not request.user.is_authenticated():
		return HttpResponseRedirect(reverse('blog_index'))

	entry = BlogItem()
	entry.pub_date = datetime.datetime.now()
	entry.headline = request.POST['headline']
	entry.summary = request.POST['summary']
	entry.body = request.POST['body']
	entry.author = request.user.username
	entry.save()
	return HttpResponseRedirect(entry.get_absolute_url())

