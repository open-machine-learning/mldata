from django.db import transaction
from django import forms
from repository.models import Task, Challenge, Result
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

class ResultForm(forms.ModelForm):
    task = forms.ModelChoiceField(queryset=Task.objects.all(), required=True)
    challenge = forms.ModelChoiceField(queryset=Challenge.objects.all(), required=False)
    output_file = forms.FileField(required=True)

    class Meta:
        model = Result

@transaction.commit_on_success
def edit(request):
    if not request.user.is_authenticated():
        if request.method == 'POST':
            next = '?next=' + request.POST['next']
        else:
            next = ''
        return HttpResponseRedirect(reverse('user_signin') + next)

    if request.method == 'POST':
        # work around a peculiarity within django
        result = None
        id = int(request.POST['id'])
        if id > 0:
            try:
                result = Result.objects.get(pk=id)
                form = ResultForm(request.POST, instance=result)
            except Result.DoesNotExist:
                form = ResultForm(request.POST)
        else:
            form = ResultForm(request.POST)

        if form.is_valid():
            if not result:
                result = Result()
            result.content = form.cleaned_data['content']
            result.title = form.cleaned_data['title']
            result.save()
            return HttpResponseRedirect(form.cleaned_data['next'])
        else:
			info_dict['result_form'] = ResultForm(request)
			return render_to_response('solution/item_edit.html', info_dict)
    return HttpResponseRedirect(reverse('repository_index'))
