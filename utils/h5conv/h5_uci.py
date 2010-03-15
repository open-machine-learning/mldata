import h5py, os, numpy
import base



class UCI2H5(base.Converter):
    """Convert a file from UCI to HDF5."""

    def get_comment(self, fname):
        name = '.'.join(fname.split('.')[:-1])
        if not name:
            name = '.'.join(fname.split('-')[:-1])

        if os.path.exists(name + '.names'):
            fp = open(name + '.names', 'r')
        elif os.path.exists(name + '.info'):
            fp = open(name + '.info', 'r')
        else:
            return None

        comment = ''.join(fp.readlines())
        fp.close()
        return comment


    def _ignore_line(self, line):
        line = line.strip()
        if not line:
            return True
        if line.startswith(';;;'):
            return True

        return False


    def _parse(self, fname):
        fp = open(fname, 'r')
        lineno = 0
        num_items = None
        data = []

        for line in fp:
            lineno += 1

            if self._ignore_line(line):
                continue

            items = line.strip().split(',')
            if not num_items: # do some init
                num_items = len(items)
                for i in xrange(num_items):
                    data.append([])

            for i in xrange(len(items)):
                item = items[i].strip()
                if not item:
                    continue

                try:
                    if item == '?': # missing value
                        item = numpy.nan
                    data[i].append(item)
                except IndexError:
                    self.warn('Index Error in line ' + str(lineno) + ', column ' + str(i))

        fp.close()
        return data


    def get_data(self, fname):
        order = []
        predata = self._parse(fname)
        data = {}

        for i in xrange(len(predata)):
            arr = numpy.array(predata[i])
            try:
                name = 'int' + str(i)
                data[name] = arr.astype(numpy.int)
            except ValueError:
                try:
                    name = 'double' + str(i)
                    data[name] = arr.astype(numpy.double)
                except ValueError:
                    name = 'str' + str(i)
                    data[name] = arr.astype(self.str_type)
            order.append(name)

        return {'names':order, 'order':order, 'data':data}
