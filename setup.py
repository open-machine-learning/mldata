#!/usr/bin/env python
import tarfile
import os

src = "http://lemonet.eu/static/"
out_dir = "media/"
file_name = "private.tar.gz"

def download(url):
    """Copy the contents of a file from a given URL
    to a local file.
    """
    import urllib
    webFile = urllib.urlopen(url)
    localFile = open(out_dir + file_name, 'w')
    localFile.write(webFile.read())
    webFile.close()
    localFile.close()

def install():
    print 'Creating database... '
    os.system("python manage.py syncdb --noinput")
    print 'Loading fixtures... '
    os.system("python manage.py loaddata `find ./ -name '*.json'`")

    try:
        print 'Downloading %s... ' % (file_name,)
        download(src + file_name)
    except IOError:
        print "IOError"
        return
        
    print 'Extracting %s... ' % (file_name,)
    tfile = tarfile.open(out_dir + file_name, 'r:gz')
    tfile.extractall('media')
    print 'Removing %s... ' % (file_name,)
    os.remove(out_dir + file_name)

    print "Done!"

if __name__ == '__main__':
    import sys
    if sys.argv[1] == "install":
        install()
    else:
        import os
        print 'usage: python %s install' % os.path.basename(sys.argv[0])