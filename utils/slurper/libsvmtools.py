import os, bz2
from slurper import Slurper
from parser.libsvmtoolshtmlparser import LibSVMToolsHTMLParser



class LibSVMTools(Slurper):
    """Slurp from LibSVMTools."""
    url = 'http://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/'
    format = 'libsvm'

    def skippable(self, name):
        return False # allow everything now

        if name == 'australian':
            return False
        elif name == 'colon-cancer':
            return False
        elif name.startswith('duke'):
            return False
        elif name == 'ijcnn1':
            return False
        elif name == 'splice':
            return False

        elif name == 'connect-4':
            return False
        elif name == 'dna':
            return False
        elif name == 'sector':
            return False

        elif name == 'yeast':
            return False
        elif name == 'scene-classification':
            return False

        elif name == 'cadata':
            return False
        elif name == 'triazines':
            return False

        return True


    def unzip(self, oldnames):
        newnames = []
        for o in oldnames:
            o = self.get_dst(o)
            n = o.replace('.bz2', '')
            if o.endswith('.bz2'):
                self.progress('Decompressing ' + o, 4)
                old = bz2.BZ2File(o, 'r')
                new = open(n, 'w')
                try:
                    new.write(old.read())
                except EOFError:
                    self.warn("Can't decompress properly, skipping " + o)
                    continue
                finally:
                    old.close()
                    new.close()
            newnames.append(n)
        return newnames


    def unzip_rm(self, filenames):
        for fname in filenames:
            if fname.endswith('.bz2'):
                os.remove(os.path.join(self.output, fname.replace('.bz2', '')))


    def _add_1(self, parsed, fname):
        """Add one object.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param fname: name of file to add
        @type fname: string
        """
        self.create_data(parsed, fname)


    def _add_2(self, parsed):
        """Add two objects.

        Either 1 + scaled version or 1 + split file.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """
        if parsed['files'][1].endswith('scale'):
            self._add_1(parsed, parsed['files'][0])
            parsed['name'] += '_scale'
            self._add_1(parsed, parsed['files'][1])
        else:
            self._add_datatask(parsed, parsed['files'])


    def _add_3(self, parsed):
        """Add three objects.

        Either 1 + 2 splits, or 1 + split + scaled or 1 + 2 scaled

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """
        fname = parsed['files'][2]
        if fname.endswith('.r') or fname.endswith('.val'):
            self._add_datatask(parsed, parsed['files'])
        elif fname.endswith('.t'): # bit of a weird case: binary splice
            self._add_datatask(parsed, [parsed['files'][0], parsed['files'][2]])
            parsed['name'] += '_scale'
            self._add_1(parsed, parsed['files'][1])
        elif fname.endswith('scale'): # another weird case: multiclass covtype
            self._add_1(parsed, parsed['files'][0])
            parsed['name'] += '_scale01'
            self._add_1(parsed, parsed['files'][1])
            parsed['name'] += '_scale'
            self._add_1(parsed, parsed['files'][2])
        else:
            self.progress('unknown ending of file ' + fname)


    def _add_4(self, parsed):
        """Add four objects.

        Either 1 + 3 splits, or 1 + split + scaled + scaled split

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """
        if parsed['files'][3].endswith('.val'):
            self._add_datatask(parsed, parsed['files'])
        else:
            self._add_datatask(parsed, parsed['files'][0:2])
            parsed['name'] += '_scale'
            self._add_datatask(parsed, parsed['files'][2:4])


    def _add_5(self, parsed):
        """Add five objects, 1 + 4 splits.

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """

        self._add_datatask(parsed, parsed['files'])


    def _add_10(self, parsed):
        """Add ten objects, 1 + 9 splits

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        """
        self._add_datatask(parsed, parsed['files'])


    def _add_datatask(self, parsed, fnames):
        """Add Data + Task to mldata.org

        @param parsed: parsed information from HTML
        @type parsed: dict with fields name, source, description, type, files
        @param fnames: filenames of related to this task
        @type fnames: list of strings
        """
        tmp = self.concat(fnames)
        data = self.create_data(parsed, tmp)
        self.create_task(parsed, data, fnames)
        os.remove(tmp)


    def add(self, parsed):
        self.progress('Adding to repository.', 3)
        oldnames = parsed['files']
        parsed['files'] = self.unzip(parsed['files'])
        num = len(parsed['files'])
        if num == 1:
            self._add_1(parsed, parsed['files'][0])
        elif num == 2:
            self._add_2(parsed)
        elif num == 3:
            self._add_3(parsed)
        elif num == 4:
            self._add_4(parsed)
        elif num == 5:
            self._add_5(parsed)
        elif num == 10:
            self._add_10(parsed)

        self.unzip_rm(oldnames)



    def slurp(self):
        parser = LibSVMToolsHTMLParser()
        self.handle(parser, self.url + 'binary.html', 'Binary')
        parser = LibSVMToolsHTMLParser()
        self.handle(parser, self.url + 'multiclass.html', 'MultiClass')
        parser = LibSVMToolsHTMLParser()
        self.handle(parser, self.url + 'regression.html', 'Regression')
        parser = LibSVMToolsHTMLParser()
        self.handle(parser, self.url + 'multilabel.html', 'MultiLabel')



