from slurphtmlparser import SlurpHTMLParser

class WekaHTMLParser(SlurpHTMLParser):
    """HTMLParser class for Weka."""

    def handle_starttag(self, tag, attrs):
        if self.state == 'done':
            return

        if tag == 'li':
            self.state = 'description'
        elif tag == 'a':
            href = None
            for a in attrs:
                if a[0] == 'href':
                    href = a[1]
                    break
            if href:
                if href.endswith('gz') or href.endswith('jar') or\
                    href.endswith('?download') or href.find('?use_mirror=') > -1:
                    self.current['files'].append(href)
                    self.current['name'] = href.split('/')[-1].split('.')[0]
                else:
                    self.current['source'] += href + ' '


    def handle_endtag(self, tag):
        if self.state == 'done':
            return

        if tag == 'ul': # ignore everything after first ul has ended
            self.state = 'done'
        elif tag == 'li':
            self.current['license'] = 5 # see repository/fixtures/license.json
            self.reinit()


    def handle_data(self, data):
        if self.state == 'done':
            return

        if self.state == 'description':
            self.current['description'] += data
