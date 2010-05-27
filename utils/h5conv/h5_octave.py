import h5py, numpy
import base



class OCTAVE2H5(base.H5Converter):
    """Convert a file from Octave file format to HDF5 (spec of mldata.org).


    @ivar matf: data from mat file
    @type matf: mat object
    """

    def __init__(self, *args, **kwargs):
        super(OCTAVE2H5, self).__init__(*args, **kwargs)
        self.octf = open(self.fname_in,'r')


    def _check_header(self):
	"""evidence of octave conformity (inactiv)
	
	"""
	return True
	"""
	self.octf.seek(0)
	header=self.octf.readline()
	if header.startswith('# Created by '):
		return True
	else:
	
		return False
	"""

    def _next_attr(self):
        """Returns the next atribute in the octave file

        @return (name,data): name and proper matrix of the atribute
        """
	row=1
	col=1
	name='1'
	data=[]
	 
	line = self.octf.readline()
	while not line.startswith('#'):
		if line == '':
			return {'name':'','data':[]}
		line = self.octf.readline()
	
			
	# metadata
	while line.startswith('#'):
		sp=line.split(': ')
		if sp[0]=='# name':
			name=sp[1][:-1]
		if sp[0]=='# rows':
			rows=int(sp[1])
		if sp[0]=='# columns':
			col=int(sp[1])
		line = self.octf.readline()	
	# matrix
	lpos=self.octf.tell()
	while (not line.startswith('#')) & (not line == ''):
		if line.startswith(' '):
			line=line[1:]
		sp=line[:-1].split(' ')
		conv_sp=[]
		try:
			for i in sp:
				conv_sp.append(int(i))
		except ValueError:
			for i in sp:
				conv_sp.append(float(i))
		except ValueError:	
			conv_sp.append(sp)
					
		data.append(conv_sp)
		lpos=self.octf.tell()
		line = self.octf.readline()
	self.octf.seek(lpos)
	return  {'name':name,'data':data}				



    def get_data(self):
	data={}
	names=[]

	# header check
	if not self._check_header():
		raise ConversionError('Header check failed')
        	return {'names':[], 'ordering':names, 'data':data}

	attr=self._next_attr()
	while attr['name']!='':
		if attr['name']!='__nargin__':
	        	data[attr['name']]=attr['data']
       			names.append(attr['name'])  
		attr=self._next_attr()
	if (data.keys==[]):
		raise ConversionError('empty conversion')
        return {'names':[], 'ordering':names, 'data':data}



class H52OCTAVE(base.H5Converter):
    """Convert a file from HDF5 (spec of mldata.org) to Octave file format


    @ivar fname_in: filename to read data from
    @type fname_in: string
    @ivar fname_out: filename to write converted data to
    @type fname_out: string

    """

    def _oct_header(self):
	return '# Created by mldata.org for Octave 3.0.1\n'
    
    def _print_meta(self,attr,name):
	"""Return a string of metainformation

	@return meta: string of attr informations
	"""
	meta='# name: ' + name + '\n'
	if attr.shape ==(1,):
		meta+='# type: scalar\n'
		return meta
	else: 
		meta+='# type: matrix\n'
	meta+='# rows: ' + str(attr.shape[1]) + '\n'
	meta+='# columns: ' + str(attr.shape[0]) + '\n'

 	return meta

    def _print_data(self,attr):
	"""Return a string of data  

	@return data: string of attr content
	"""
	data=''
	for i in attr:
		for j in i:
			data+=' ' + str(j)
		data+='\n'
	return data


    def run(self):
        """Run the actual conversion process.

        @param in_fname: filename to read data from
        @type in_fname: string
        @param out_fname: filename to write converted data to
        @type out_fname: string
        """
	
	o = open(self.fname_out,'w')
        h = h5py.File(self.fname_in, 'r')

	out=self._oct_header()	

	for i in list(h['/data/']):
		out+=self._print_meta(h['/data/' + i][...],i)
		out+=self._print_data(h['/data/'+i][...])
	
        h.close()
	o.writelines(out)
	o.close()
