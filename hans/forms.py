from django import forms


class BootstrapFormMixin:
    """Give every widget the Bootstrap 5 input class so forms render styled with {{ form.as_div }}."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            field.widget.attrs['class'] = f"{field.widget.attrs.get('class', '')} {css}".strip()
