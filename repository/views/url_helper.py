from django.core.urlresolvers import reverse

class UrlHelper(object):
    """This class helps generating reverse urls for different actions on
    a given object."""
    def __init__(self, obj, *args):
        self.klassname = type(obj).__name__.lower()
        self.args = args

    def activate(self):
        return reverse(self._method('activate'), args=self.args)

    def edit(self):
        return reverse(self._method('edit'), args=self.args)

    def delete(self):
        return reverse(self._method('delete'), args=self.args)

    def _method(self, action):
        return 'repository.views.' + self.klassname + '.' + action