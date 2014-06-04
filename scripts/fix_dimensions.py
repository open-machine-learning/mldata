from repository.models import *
from settings import *
import os
import ml2h5.data

for d in Data.objects.all():
        #s='%s\t%s\t%s' % (d.format, d.file.name, '%s_v%d%s' % (d.slug, d.version, ext))
        #dst=os.path.join(MEDIA_ROOT,'%s_v%d%s' % (d.slug, d.version, ext))
        src1=os.path.join(MEDIA_ROOT, d.file.name)
        if not os.path.exists(src1):
            print "file missing",src1
        elif src1.endswith('.h5'):
            (d.num_instances, d.num_attributes) = ml2h5.data.get_num_instattr(src1)
            d.save(silent_update=True)
        else:
            print "not hdf5 ignoring", src1
