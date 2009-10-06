from django.db import models


class Repository(models.Model):
    pub_date = models.DateTimeField()
    mod_date = models.DateTimeField()
    version = models.IntegerField()
    summary = models.CharField(max_length=255)
    description = models.TextField()
    urls = models.CharField(max_length=255)
    publications = models.CharField(max_length=255)
    license = models.CharField(max_length=255)

    class Meta:
        ordering = ('-pub_date',)
        get_latest_by = 'pub_date'

    def __unicode__(self):
        return unicode(self.summary)


class Data(Repository):
    source = models.CharField(max_length=255)
    format = models.CharField(max_length=16) # CSV, ARFF, netCDF, HDF5, ODBC
    measurement_details = models.TextField()
    usage_scenario = models.TextField()

    def get_absolute_url(self):
        modulator = 16384
        return "/repository/data/%s/%s/" % (self.id % modulator, self.id)


class Task(Repository):
    format_input = models.CharField(max_length=255)
    format_output = models.CharField(max_length=255)
    training_test_offset = models.IntegerField()
    performance_measure = models.CharField(max_length=255)
    data = models.ManyToManyField(Data)


class Solution(Repository):
    feature_processing = models.CharField(max_length=255)
    parameters = models.CharField(max_length=255)
    os = models.CharField(max_length=255)
    code = models.TextField()
    score = models.CharField(max_length=255)
    task = models.ForeignKey(Task)

