"""
All custom blog logic is kept here
"""

import datetime
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from blog.models import Post


def new(request):
	if not request.user.is_authenticated():
		return HttpResponseRedirect(reverse('blog_index'))

	return render_to_response('blog/new.html', { 'user': request.user })


def post(request):
	if not request.user.is_authenticated():
		return HttpResponseRedirect(reverse('blog_index'))

	post = Post()
	post.pub_date = datetime.datetime.now()
	post.headline = request.POST['headline']
	post.summary = request.POST['summary']
	post.body = request.POST['body']
	post.author_id = request.user.id
	post.save()
	return HttpResponseRedirect(post.get_absolute_url())

