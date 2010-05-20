import os, urllib
from slurper import Slurper
from parser.ucihtmlparser import UCIHTMLParser, UCIIndexParser, UCIDirectoryParser



class UCI(Slurper):
    """Slurp from UCI."""
    url = 'http://archive.ics.uci.edu/ml/datasets.html'
    format = 'uci'

    def skippable(self, name):
        return False # allow everything now

        if name == 'Abalone':
            return False
        elif name == 'Dermatology':
            return False
        elif name == 'Kinship':
            return False
        elif name == 'Sponge':
            return False
        elif name == 'Zoo':
            return False
        elif name == 'Statlog (Heart)':
            return False
        elif name == 'Gisette':
            return False

        return True


    def get_dst(self, filename):
        try:
            f = filename.split('machine-learning-databases/')[1]
        except IndexError:
            f = filename.split('databases/')[1]
        return os.path.join(self.output, f)


    def expand_dir(self, dirnames):
        filenames = []
        for d in dirnames:
            if not d.endswith('/'):
                d += '/'
            url = self.url + '/' + d
            p = UCIDirectoryParser(d)
            try:
                r = urllib.urlopen(url)
            except IOError, err:
                self.warn('IOError: ' + str(err))
                return []
            p.feed(''.join(r.readlines()).replace('\\"', '"'))
            r.close()
            p.close()
            filenames.extend(p.filenames)
        return filenames


    def add(self, parsed):
        # only accept bla.data + bla.names for the time being...
        files = {}
        ignore_data = False
        is_bagofstuff = False
        for f in parsed['files']:
            if (f.endswith('.data') or f.endswith('-data')) and not ignore_data:
                files['data'] = f
                ignore_data = True
            elif (f.endswith('.names') or f.endswith('.info')) and 'data' in files and\
                files['data'].split('.')[:-1] == f.split('.')[:-1]:
                files['names'] = f
        if len(files) != 2:
            self.progress('Unknown composition of data files, adding bag-of-stuff!', 3)
            is_bagofstuff = True
            files['data'] = self.get_bagofstuff(parsed['files'])
            self.problematic.append(parsed['name'])
        else:
            self.progress('Adding to repository.', 3)
            files['data'] = self.get_dst(files['data'])
            data = self.create_data(parsed, files['data'])
            if data and parsed['task'] != 'N/A':
                self.create_task(parsed, data)

        if is_bagofstuff:
            os.remove(files['data'])


    def slurp(self):
        parser = UCIIndexParser()
        try:
            response = urllib.urlopen(self.url)
        except IOError, err:
            self.warn('IOError: ' + str(err))
            return
        parser.feed(''.join(response.readlines()).replace('\\"', '"'))
        response.close()
        #parser.feed(self.fromfile('datasets.html'))
        parser.close()

        for u in set(parser.uris):
            p = UCIHTMLParser()
            url = '/'.join(self.url.split('/')[:-1]) + '/' + u
            self.handle(p, url)
