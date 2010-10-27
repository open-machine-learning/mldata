from repository.models import *
from settings import *
import os

#os.rename
for d in Data.objects.all():
	print d.file.name
