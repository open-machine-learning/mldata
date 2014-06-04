#!/usr/bin/env python
import tarfile
import os

src = "http://mldata.org/repository/data/download/%s/"
out_dir = "media/private/data/"
file_name = "private.tar.gz"

file_in = ["abalone", "book-crossing-ratings-10", "fish_killer", "regression-datasets-cpu_small"]
file_out = ["abalone", "book-crossing-ratings", "fish-killer", "regression-cpu-small"]

def download(url, localfile):
    """Copy the contents of a file from a given URL
    to a local file.
    """
    import urllib
    webFile = urllib.urlopen(src % (url,))
    localFile = open(out_dir + localfile + ".h5", 'w')
    localFile.write(webFile.read())
    webFile.close()
    localFile.close()

def install():
    print 'Creating database... '
    os.system("python manage.py syncdb --noinput")
    print 'Loading fixtures... '
    os.system("python manage.py loaddata `find ./ -name '*.json'`")

    for i in range(0,len(file_in)):
        try:
            file_name = file_in[i]
            print 'Downloading %s... ' % (file_name,)
            download(file_name,file_out[i])
        except IOError:
            print "IOError"
            return
        
    print "Done!"
    print "Type 'python manage.py runserver' to start!"

if __name__ == '__main__':
    import sys
    if sys.argv[1] == "install":
        install()
    else:
        import os
        print 'usage: python %s install' % os.path.basename(sys.argv[0])