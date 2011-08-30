from django import forms
from registration.forms import RegistrationForm
from captcha.fields import ReCaptchaField
from django.conf import settings
from django.utils.encoding import smart_unicode, force_unicode
from django.utils.translation import ugettext_lazy as _
from django.forms.forms import BoundField
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

class RegistrationFormCaptcha(RegistrationForm):
    captcha = ReCaptchaField()
    remote_ip = forms.IPAddressField(widget=forms.HiddenInput()) # Not rendered in templates -- value must be set by the view.
    
    def clean(self):
        default_error_messages = {
            'captcha_invalid': _(u'Incorrect, please try again.')
        }
        cleaned_data = super(RegistrationFormCaptcha, self).clean()
        remote_ip = cleaned_data.get('remote_ip')
        captcha = cleaned_data.get('captcha')

        recaptcha_challenge_value = smart_unicode(values[0])
        recaptcha_response_value = smart_unicode(values[1])
        
        if 'RECAPTCHA_USE_SSL' in settings.__dict__.items()[0][1]:
            use_ssl = settings.RECAPTCHA_USE_SSL
        else:
            use_ssl = False
            
        check_captcha = captcha.submit(recaptcha_challenge_value, 
            recaptcha_response_value, settings.RECAPTCHA_PRIVATE_KEY, remote_ip, use_ssl=use_ssl)

        if not check_captcha.is_valid:
            msg = default_error_messages['captcha_invalid']
            self._errors['captcha'] = self.error_class([msg])
            del cleaned_data['captcha']
            
        return self.cleaned_data

    def _html_output(self, normal_row, error_row, row_ender, help_text_html, errors_on_separate_row):
        # Customized to handle special case for reCaptcha forms (not rendering remote_ip field)
        "Helper function for outputting HTML. Used by as_table(), as_ul(), as_p()."
        top_errors = self.non_field_errors() # Errors that should be displayed above all fields.
        output, hidden_fields = [], []

        for name, field in self.fields.items():
            html_class_attr = ''
            bf = BoundField(self, field, name)
            bf_errors = self.error_class([conditional_escape(error) for error in bf.errors]) # Escape and cache in local variable.
            if not bf.is_hidden:
                # Create a 'class="..."' atribute if the row should have any
                # CSS classes applied.
                css_classes = bf.css_classes()
                if css_classes:
                    html_class_attr = ' class="%s"' % css_classes

                if errors_on_separate_row and bf_errors:
                    output.append(error_row % force_unicode(bf_errors))

                if bf.label:
                    label = conditional_escape(force_unicode(bf.label))
                    # Only add the suffix if the label does not end in
                    # punctuation.
                    if self.label_suffix:
                        if label[-1] not in ':?.!':
                            label += self.label_suffix
                    label = bf.label_tag(label) or ''
                else:
                    label = ''

                if field.help_text:
                    help_text = help_text_html % force_unicode(field.help_text)
                else:
                    help_text = u''

                output.append(normal_row % {
                    'errors': force_unicode(bf_errors),
                    'label': force_unicode(label),
                    'field': unicode(bf),
                    'help_text': help_text,
                    'html_class_attr': html_class_attr
                })

        if top_errors:
            output.insert(0, error_row % force_unicode(top_errors))

        return mark_safe(u'\n'.join(output))
