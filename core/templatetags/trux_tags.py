from django import template

register = template.Library()

@register.filter
def primera_palabra(value):
    if not value:
        return ''
    return str(value).split()[0]
