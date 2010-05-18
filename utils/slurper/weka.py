import os, shutil, subprocess
from slurper import Slurper
from parser.wekahtmlparser import WekaHTMLParser



class Weka(Slurper):
    """Slurp from Weka."""
    url = 'http://www.cs.waikato.ac.nz/~ml/weka/index_datasets.html'
    format = 'arff'

    def skippable(self, name):
        return False # allow everything now

        if name == 'datasets-arie_ben_david':
            return False
        elif name == 'agridatasets':
            return False

        return True



    def _unzip_traverse(self, dir, may_unzip=False):
        """Traverse directories to recursively unzip archives.

        @param dir: directory to look in
        @type dir: string
        @param may_unzip: if this dir may unzip files (to prevent endless loop)
        @type may_unzip: boolean
        @return: unzipped filenames
        @rtype: list of strings
        """
        items = []
        for item in os.listdir(dir):
            item = os.path.join(dir, item)
            if os.path.isdir(item):
                items.extend(self._unzip_traverse(item, True))
            elif item.endswith('.arff'):
                items.append(item)
            elif may_unzip: # assuming another archive
                items.extend(self._unzip_do(item))
        return items


    def _unzip_do(self, zip):
        """Actually perform the unzip process.

        @param zip: name of zipped file
        @type zip: string
        @return: unzipped filenames
        @rtype: list of strings
        """
        dir = os.path.join(self.output, zip.split(os.sep)[-1].split('.')[0])

        cmd = 'cd ' + dir + ' && '
        if zip.endswith('.jar'):
            cmd += 'jar -xf ' + zip
        elif zip.endswith('.bz2'):
            cmd += 'tar -xjf ' + zip
        elif zip.endswith('.gz'):
            cmd += 'tar -xzf ' + zip
        elif zip.endswith('.zip'):
            cmd += 'unzip -o -qq ' + zip
        else:
            return []

        if not os.path.exists(dir):
            os.makedirs(dir)
        if not subprocess.call(cmd, shell=True) == 0:
            raise IOError('Unsuccessful execution of ' + cmd)

        return self._unzip_traverse(dir, False)



    def unzip(self, oldnames):
        newnames = []
        for o in oldnames:
            o = self.get_dst(o)
            self.progress('Decompressing ' + o, 4)
            newnames.extend(self._unzip_do(o))

        return newnames


    def unzip_rm(self, fnames):
        for f in fnames:
            dir = os.path.join(self.output, f.split(os.sep)[-1].split('.')[0])
            shutil.rmtree(dir)


    def get_dst(self, filename):
        f = filename.split('/')[-1].split('?')[0]
        return os.path.join(self.output, f)


    def add(self, parsed):
        self.progress('Adding to repository.', 3)

        orig = parsed['name']
        for f in self.unzip(parsed['files']):
            splitname = ''.join(f.split(os.sep)[-1].split('.')[:-1])
            parsed['name'] = orig + ' ' + splitname
            if self._data_exists(parsed['name']) and not self.options.convert_exist:
                self.warn('Dataset ' + parsed['name'] + ' already exists, skipping!')
                continue
            else:
                self.create_data(parsed, f)
        self.unzip_rm(parsed['files'])


    def slurp(self):
        parser = WekaHTMLParser()
        self.handle(parser, self.url)



