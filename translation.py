from modeltranslation.translator import register, TranslationOptions

from .models import Production, PriceCategory


@register(Production)
class ProductionTranslationOptions(TranslationOptions):
    fields = ('name', 'description')

@register(PriceCategory)
class PriceCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)
