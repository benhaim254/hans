from django import forms


class BootstrapFormMixin:
    """Give every widget the Bootstrap 5 input class so forms render styled with {{ form.as_div }}."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                css = 'form-select'
            else:
                css = 'form-control'
            field.widget.attrs['class'] = f"{field.widget.attrs.get('class', '')} {css}".strip()
