"""
Model classes for app Preferences
"""

from django.db import models

class Preferences(models.Model):
    """The preferences.

    @cvar name: name of the object
    @type name: string
    @cvar max_data_size: maximum size of Data files for slurp/upload
    @type max_data_size: integer
    """
    name = models.CharField(max_length=42, unique=True)
    max_data_size = models.IntegerField()

    def __unicode__(self):
        return unicode(self.name)


