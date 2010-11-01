from repository.models import *
from settings import *
import os

for d in Data.objects.all():
        #s='%s\t%s\t%s' % (d.format, d.file.name, '%s_v%d%s' % (d.slug, d.version, ext))
        #dst=os.path.join(MEDIA_ROOT,'%s_v%d%s' % (d.slug, d.version, ext))
        src1=os.path.join(MEDIA_ROOT, d.file.name)
        if not os.path.exists(src1):
                print "file missing",src1
	print d.format
