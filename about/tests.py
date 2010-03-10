from django.test import TestCase

class AboutTest(TestCase):
    # local urls won't work, coz templates refer to repository_index
    #urls = 'about.urls'

    def test_index(self):
        r = self.client.get('/about/')
        self.assertEqual(r.context['section'], 'about')
        self.assertTemplateUsed(r, 'about/motivation.html')

    def test_license(self):
        r = self.client.get('/about/license/')
        self.assertEqual(r.context['section'], 'about')
        self.assertTemplateUsed(r, 'about/license.html')

    def test_hdf5(self):
        r = self.client.get('/about/hdf5/')
        self.assertEqual(r.context['section'], 'about')
        self.assertTemplateUsed(r, 'about/hdf5.html')

    def test_related(self):
        r = self.client.get('/about/related/')
        self.assertEqual(r.context['section'], 'about')
        self.assertTemplateUsed(r, 'about/related.html')

    def test_impressum(self):
        r = self.client.get('/about/impressum/')
        self.assertEqual(r.context['section'], 'about')
        self.assertTemplateUsed(r, 'about/impressum.html')

    def test_tos(self):
        r = self.client.get('/about/tos/')
        self.assertEqual(r.context['section'], 'about')
        self.assertTemplateUsed(r, 'about/tos.html')

