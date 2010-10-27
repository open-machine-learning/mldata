from repository.models import *
from settings import *
import os

for d in Data.objects.all():
        #try:
                dummy, ext = os.path.splitext(d.file.name)
                if ext in ('.gz', '.zip', '.bz2', '.rar'):
                        dummy, ext2 = os.path.splitext(dummy)
                        ext=ext2+ext

                #s='%s\t%s\t%s' % (d.format, d.file.name, '%s_v%d%s' % (d.slug, d.version, ext))
                #dst=os.path.join(MEDIA_ROOT,'%s_v%d%s' % (d.slug, d.version, ext))
                src1=os.path.join(MEDIA_ROOT, d.file.name)
                dst1=os.path.join(MEDIA_ROOT,'data/%s%s' % (d.slug, ext))

                bn=os.path.basename(d.file.name)
                src2=os.path.join(MEDIA_ROOT, 'data', 'original', bn)
                dst2=os.path.join(MEDIA_ROOT,'data/original/%s.%s' % (d.slug, d.format))
                if os.path.exists(src1) and src1 != dst1:
                        print "renaming file",src1,dst1
                        os.rename(src1, dst1)
                if not '.tar' in src2 and os.path.exists(src2) and src2 != dst2:
                        print "renaming original", src2,dst2
                        os.rename(src2, dst2)
                d.file.name=dst1
                d.save(silent_update=True)

                if not os.path.exists(src1):
                        print "file missing",src1
        #except:
        #        print
        #        print "ERROR processing", d.name, d.file.name, "...deleting"
        #        print d.user, d.pub_date, d.tags
        #        #import pdb
        #        #pdb.set_trace()
        #        #d.delete()
        #        print
