from django.db import models

class Hello(models.Model):
    afield = models.CharField(max_length=255)

    def __unicode__(self):
        return self.afield
