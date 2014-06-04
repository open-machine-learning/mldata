"""
Views for app Blog
"""

import datetime
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.template import RequestContext
from blog.models import Post, PostForm



def new(request):
    """View to make a new blog post.

    @param request: request data
    @type request: Django request
    @return a view page to make a new blog post
    @rtype: Django response
    """
    if not request.user.is_authenticated():
        redirect_to = reverse('user_signin') + '?next=' + reverse(new)
        return HttpResponseRedirect(redirect_to)

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            if request.POST.has_key('preview'):
                preview = {
                    'headline': form.cleaned_data['headline'],
                    'summary': form.cleaned_data['summary'],
                    'body': form.cleaned_data['body'],
                }
            else:
                post = Post()
                post.pub_date = datetime.datetime.now()
                post.headline = form.cleaned_data['headline']
                post.summary = form.cleaned_data['summary']
                post.body = form.cleaned_data['body']
                post.author_id = request.user.id
                post.save()
                return HttpResponseRedirect(post.get_absolute_url())
    else:
        preview = False
        form = PostForm()

    info_dict = {
        'request': request,
        'form': form,
        'preview': preview,
        'section': 'blog',
        'user': request.user,
    }
    return render_to_response('blog/new.html', info_dict,
                              context_instance=RequestContext(request))
