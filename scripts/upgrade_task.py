from repository.models import *
from settings import *
import os
import h5py
from ml2h5.task import conv_idx2image,update_data

for t in Task.objects.all():
    #s='%s\t%s\t%s' % (d.format, d.file.name, '%s_v%d%s' % (d.slug, d.version, ext))
    #dst=os.path.join(MEDIA_ROOT,'%s_v%d%s' % (d.slug, d.version, ext))
    src1=os.path.join(MEDIA_ROOT, t.file.name)
    if os.path.exists(src1):
        h5=h5py.File(src1,'r')
        taskinfo={}
        for field in list(h5['task']):
            taskinfo[field]=h5['task'][field][...]
        if taskinfo.has_key('train_idx'):
            if not taskinfo.has_key('val_idx'): 
                taskinfo['val_idx']=[]        
            if not taskinfo.has_key('test_idx'): 
                taskinfo['test_idx']=[]        
            data_size=t.data.num_instances
            taskinfo['data_split']=conv_idx2image(taskinfo['train_idx'],taskinfo['val_idx'],taskinfo['test_idx'],data_size)
            taskinfo['data_size']=data_size
            del taskinfo['train_idx']
            del taskinfo['val_idx']
            del taskinfo['test_idx']
            update_data(h5,taskinfo)
        h5.close()        
