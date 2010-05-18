from slurphtmlparser import SlurpHTMLParser



class LibSVMToolsHTMLParser(SlurpHTMLParser):
    """HTMLParser class for LibSVMTools."""

    def handle_starttag(self, tag, attrs):
        if tag == 'h2': # new data starts here
            self.state = 'name'
        elif tag == 'a' and self.state == 'file':
            self.current['files'].append(attrs[0][1])
        elif tag == 'a' and self.state == 'source':
            self.current['source'] += ' ' + attrs[0][1] + ' '


    def handle_endtag(self, tag):
        if tag == 'h2':
            self.state = None
        elif tag == 'ul' and self.state: # new data ends here
            self.current['source'] = self.current['source'].strip()
            self.current['description'] = self.current['description'].strip()
            self.current['license'] = 4 # see repository/fixtures/license.json
            self.reinit()


    def handle_data(self, data):
        if self.state == 'name':
            self.current['name'] = data
            return
        elif data.startswith('Source'):
            self.state = 'source'
            return
        elif data.startswith('Files'):
            self.state = 'file'
            return
        elif data.startswith('Preprocessing') or data.startswith('# '):
            self.state = None

        if self.state == 'source':
            self.current['source'] += data
        elif not self.state == 'file':
            self.current['description'] += data


