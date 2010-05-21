from HTMLParser import HTMLParser

class SlurpHTMLParser(HTMLParser):
    """Base class for slurping HTMLParser."""

    def _clean(self, fieldnames):
        """Clean the parsed fieldnames.

        @param field: the fieldnames to clean
        @type field: string
        """
        for f in fieldnames:
            # unicode conversion prevents django errors when adding to DB
            if f == 'publications':
                pubs = []
                for p in self.current[f]:
                    pubs.append(unicode(p.strip(), 'latin-1'))
                self.current[f] = pubs
            else:
                self.current[f] = unicode(self.current[f].strip(), 'latin-1')


    def reinit(self):
        """Reset a few instance variables."""
        if hasattr(self, 'current'):
            if self.current['name']:
                self._clean(['summary', 'description', 'source', 'publications'])
            if self.current['task'] and self.current['task'] not in ('N/A', 'NA'):
                # django url doesn't like args with slash, needs replace for tag
                self.current['tags'].append(self.current['task'].replace('/', ''))
            self.datasets.append(self.current)

        self.current = {
            'name': '',
            'source': '',
            'publications': [],
            'description': '',
            'summary': '',
            'task': '',
            'tags': [],
            'files': [],
            'license': 1,
        }
        self.state = None


    def __init__(self, *args, **kwargs):
        """Constructor to initialise instance variables.

        @ivar datasets: collection of datasets
        @type datasets: list of dicts
        @ivar current: current dataset
        @type current: dict with fields name, source, description, files
        @ivar state: state of parser
        @type state: string
        """
        HTMLParser.__init__(self, *args, **kwargs)
        self.datasets = []
        self.reinit()
