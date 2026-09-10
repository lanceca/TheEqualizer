from django import template

from home.models import MobileAppSettings


register = template.Library()


@register.simple_tag
def get_mobile_app_settings():
    return MobileAppSettings.get_solo()
