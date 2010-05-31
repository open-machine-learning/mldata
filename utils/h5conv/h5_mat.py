import h5py, numpy
import base
from scipy.io import savemat,loadmat



class MAT2H5(base.H5Converter):
    """Convert a file from MAT to HDF5 (spec of mldata.org).


    @ivar matf: data from mat file
    @type matf: mat object
    """

    def __init__(self, *args, **kwargs):
        super(MAT2H5, self).__init__(*args, **kwargs)
        self.matf = loadmat(self.fname_in,matlab_compatible=True)


    def get_contents(self):
	if self.matf.has_key('__globals__'):
		del self.matf['__globals__']
        data = self.matf
        ordering = self.matf.keys()

        return {'names':[], 'ordering':ordering, 'data':data}



class H52MAT(base.H5Converter):
    """Convert a file from HDF5 (spec of mldata.org) to MAT


    @ivar fname_in: filename to read data from
    @type fname_in: string
    @ivar fname_out: filename to write converted data to
    @type fname_out: string

    """

    def run(self):
        """Run the actual conversion process.

        @param in_fname: filename to read data from
        @type in_fname: string
        @param out_fname: filename to write converted data to
        @type out_fname: string
        """
        m={}
        h = h5py.File(self.fname_in, 'r')
	
	for i in list(h['/data_descr/ordering']):
		m[i]=h['/data/'+i][...]
	
        h.close()
	savemat(self.fname_out,m, appendmat=False)
