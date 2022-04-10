from modeltranslation.translator import register, TranslationOptions

from .models import Production, PriceCategory


@register(PriceCategory)
class PriceCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)
