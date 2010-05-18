from HTMLParser import HTMLParser
from slurphtmlparser import SlurpHTMLParser



class UCIIndexParser(HTMLParser):
    """HTMLParser for UCI index page."""

    def __init__(self, *args, **kwargs):
        """Constructor to initialise instance variables.

        @ivar uris: collection of data URIs
        @type uris: list of strings
        """
        HTMLParser.__init__(self, *args, **kwargs)
        self.uris = []


    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for a in attrs:
                if a[0] == 'href' and a[1].startswith('datasets/'):
                    self.uris.append(a[1])
                    break



class UCIDirectoryParser(HTMLParser):
    """HTMLParser for UCI download directory page."""

    def __init__(self, *args, **kwargs):
        """Constructor to initialise instance variables.

        @ivar filenames: collection of filenames
        @type filenames: list of strings
        """
        HTMLParser.__init__(self, *args[1:], **kwargs)
        self.dir = args[0]
        self.filenames = []
        self.state = None


    def handle_starttag(self, tag, attrs):
        if tag == 'a' and self.state == 'files':
            for a in attrs:
                if a[0] == 'href' and a[1] != 'Index':
                    self.filenames.append(self.dir + a[1])

    def handle_data(self, data):
        if data == 'Parent Directory':
            self.state = 'files'



class UCIHTMLParser(SlurpHTMLParser):
    """HTMLParser class for UCI.

    @ivar pub: temporary single publication variable
    @type pub: string
    @ivar brcount: count to keep track of publication 'divisor' (== <br>)'
    @type brcount: integer
    """

    def handle_starttag(self, tag, attrs):
        if tag == 'span' and not self.state:
            for a in attrs:
                if a[0] == 'class' and a[1] == 'heading':
                    self.state = 'name'
                    break
        elif tag == 'b':
            if self.state == 'predescription':
                self.state = 'description'
            elif self.state == 'presummary':
                self.state = 'summary'
        elif tag == 'p':
            for a in attrs:
                if a[0] == 'class' and a[1] == 'small-heading':
                    if self.state == 'presource':
                        self.state = 'source'
                    elif self.state == 'source':
                        self.state = 'description'
                    break
        elif tag == 'a' and self.state == 'files':
            for a in attrs:
                if a[0] == 'href':
                    self.current['files'].append(a[1])
                    self.state = 'presummary'
                    break
        elif tag == 'a' and self.state in ('source', 'description', 'publications'):
            for a in attrs:
                if a[0] == 'href' and a[1].startswith('http://'):
                    link = '<a href="' + a[1] + '">' + a[1] + '</a> '
                    if self.state == 'publications':
                        self.pub += link
                    else:
                        self.current[self.state] += "\n" + link
                    break
        elif tag == 'br' and self.state == 'publications':
            if self.brcount == 0:
                self.brcount = 1
            elif self.brcount == 1:
                self.current['publications'].append(self.pub)
                self.pub = ''
                self.brcount = 0



    def handle_endtag(self, tag):
        if tag == 'span' and self.state == 'name':
            self.state = 'files'
        elif tag == 'p' and self.state == 'summary':
            self.state = 'predescription'
        elif tag == 'br' and self.state == 'publications':
            self.state = 'description'
        elif tag == 'table' and self.state == 'description':
            self.state = 'presource'


    def handle_data(self, data):
        if data.startswith('Citation Request'): # end of data
            self.current['description'] =\
                self.current['description'].replace('  [View Context].', '')
            pubs = []
            for p in self.current['publications']:
                pubs.append(p.replace('  [View Context].', '').replace('[Web Link]', ''))
            self.current['publications'] = pubs
            self.current['source'] =\
                self.current['source'].replace('Source:', '')
            self.current['license'] = 6 # see repository/fixtures/license.json
            self.reinit()
            return

        if self.state == 'name':
            self.current['name'] = data.replace(' Data Set', '')
        elif self.state == 'summary':
            self.current['summary'] = data[2:]
        elif self.state == 'task' and data.strip():
            self.current['task'] = data
            self.state = 'description'
        elif self.state == 'publications' and data.strip():
            self.pub += data
        elif self.state == 'description':
            if data.startswith('Associated Tasks'):
                self.state = 'task'
            elif data.startswith('Relevant Papers') or data.startswith('Papers That Cite This'):
                self.state = 'publications'
                self.pub = ''
                self.brcount = 0
            else:
                self.current['description'] += data
        elif self.state == 'source':
            self.current['source'] += data
