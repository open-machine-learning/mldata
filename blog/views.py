"""
All custom blog logic is kept here
"""

import datetime
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from blog.models import Post, PostForm


def new(request):
    if not request.user.is_authenticated():
        return HttpResponseRedirect(reverse('blog_index'))

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = Post()
            post.pub_date = datetime.datetime.now()
            post.headline = form.cleaned_data['headline']
            post.summary = form.cleaned_data['summary']
            post.body = form.cleaned_data['body']
            post.author_id = request.user.id
            post.save()
            return HttpResponseRedirect(post.get_absolute_url())
    else:
        form = PostForm()

    info_dict = {
        'user': request.user,
        'form': form,
    }
    return render_to_response('blog/new.html', info_dict)
