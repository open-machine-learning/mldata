"""
Slurp data objects from the interwebz and add them to the repository
"""

import os
from settings import PRODUCTION

if PRODUCTION:
    MAX_SIZE_DATA = 1024 * 1024 * 64 # (64 MB)
else:
    MAX_SIZE_DATA = 1024 * 1024 * 1 # (1 MB)

# strings of names of slurper classes
SLURPERS = ('LibSVMTools', 'Weka', 'UCI')



class Options(object):
    """Options to the slurper.

    @cvar output: output directory of downloads
    @type output: string
    @cvar verbose: if slurper shall run in verbose mode
    @type verbose: boolean
    @cvar download_only: if slurper shall only download files, not adding
    @type download_only: boolean
    @cvar add_only: if slurper shall only add files, not downloading
    @type add_only: boolean
    @cvar convert_exist: if data files of existing datasts shall be converted (implies download)
    @type convert_exist: boolean
    @cvar force_download: force download, even if file already exists.
    @type force_download: boolean
    @cvar source: active source to slurp from
    @type source: int
    """
    output = os.path.join(os.getcwd(), 'slurped')
    verbose = False
    download_only = False
    add_only = False
    convert_exist = False
    force_download = False
    source = None
