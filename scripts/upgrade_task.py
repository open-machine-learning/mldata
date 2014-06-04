from repository.models import *
from settings import *
import os
import h5py
from ml2h5.task import conv_idx2image,update_data

for t in Task.objects.all():
    #s='%s\t%s\t%s' % (d.format, d.file.name, '%s_v%d%s' % (d.slug, d.version, ext))
    #dst=os.path.join(MEDIA_ROOT,'%s_v%d%s' % (d.slug, d.version, ext))
    src1=os.path.join(MEDIA_ROOT, t.file.name)
    if src1=='/home/mldata/private/task/mkl-toy.txt':
        continue
    if os.path.exists(src1):
        print t, src1
        h5=h5py.File(src1,'r+')
        taskinfo={}
        for field in ('train_idx', 'val_idx', 'test_idx'):
            print field
            taskinfo[field]=[]        
            if field in h5['task'].keys():
                x=h5['task'][field][...]
                if x.ndim==1:
                   x=x.reshape(1,len(x))
                else:
                   x=x.transpose()
                y=list()
                for l in x:
                    y.append([', '.join([str(i) for i in l])])
                
                taskinfo[field]=y

        if len(taskinfo['train_idx'])>0:
            print t.data, t.data.num_instances
            data_size=t.data.num_instances
            taskinfo['data_split']=conv_idx2image(taskinfo['train_idx'],taskinfo['val_idx'],taskinfo['test_idx'],data_size)
            taskinfo['data_size']=data_size
            del taskinfo['train_idx']
            del taskinfo['val_idx']
            del taskinfo['test_idx']
            update_data(h5,taskinfo)

        for field in ('train_idx', 'val_idx', 'test_idx'):
            try:
                del h5['task'][field]
            except:
                pass

        h5.close()        
        print
