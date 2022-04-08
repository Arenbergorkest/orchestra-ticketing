from modeltranslation.translator import register, TranslationOptions

from .models import Production, PriceCategory


@register(Production)
class ProductionTranslationOptions(TranslationOptions):
    fields = ('description', 'reason')


@register(PriceCategory)
class PriceCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)
