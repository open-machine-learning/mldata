from repository.models import *
from settings import *
import os
import h5py

for d in Data.objects.all():
        #s='%s\t%s\t%s' % (d.format, d.file.name, '%s_v%d%s' % (d.slug, d.version, ext))
        #dst=os.path.join(MEDIA_ROOT,'%s_v%d%s' % (d.slug, d.version, ext))
        src1=os.path.join(MEDIA_ROOT, d.file.name)
        if not os.path.exists(src1):
                print "file missing",src1
		print d.format
        if not src1.endswith('.h5'):
                continue
        
        h5=h5py.File(src1, 'r')
        if not len(h5['/data/'].keys()):
                print "/data/ group empty... deleting",src1
                d.delete()
                if os.path.exists(src1):
                        os.remove(src1)

