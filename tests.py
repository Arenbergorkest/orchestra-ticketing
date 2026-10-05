from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.utils import translation
from django.utils.timezone import now

from .forms import OnlineOrderForm
from .models import MarketingChoice, OnlineOrder, Performance, Production


class MarketingChoiceTests(TestCase):
    def setUp(self):
        self.choice = MarketingChoice.objects.create(
            tag='website', text='Our website', translation='Onze website'
        )
        self.production = Production.objects.create(name='Form concert',
                                                    description='')
        self.production.marketing_choices.add(self.choice)
        self.performance = Performance.objects.create(
            production=self.production, date=now()
        )

    def test_translated_labels(self):
        with translation.override('en'):
            self.assertEqual(str(self.choice), 'Our website')
        with translation.override('nl-be'):
            self.assertEqual(str(self.choice), 'Onze website')

    def test_form_uses_dynamic_choices_and_stable_tags(self):
        with translation.override('nl'):
            form = OnlineOrderForm(self.performance)
            field = form.fields['marketing_feedback']
            self.assertEqual(field.clean('website'), self.choice)
            self.assertIn('Onze website', str(form['marketing_feedback']))
            self.assertIn('value="website"', str(form['marketing_feedback']))
            self.assertIsNone(field.clean(''))

    def test_form_only_offers_production_selection(self):
        form = OnlineOrderForm(self.performance)
        self.assertEqual(form.fields['marketing_feedback'].clean('website'),
                         self.choice)
        other_production = Production.objects.create(name='Other concert',
                                                     description='')
        other_choice = MarketingChoice.objects.get(tag='facebook')
        other_production.marketing_choices.add(other_choice)
        with self.assertRaises(ValidationError):
            form.fields['marketing_feedback'].clean('facebook')

    def test_removed_choice_is_retained_only_for_existing_order(self):
        self.production.marketing_choices.clear()
        form = OnlineOrderForm(self.performance)
        self.assertFalse(form.fields['marketing_feedback'].queryset.exists())
        with self.assertRaises(ValidationError):
            form.fields['marketing_feedback'].clean('website')
        order = OnlineOrder(pk=123, marketing_feedback=self.choice)
        form = OnlineOrderForm(self.performance, instance=order)
        self.assertEqual(
            form.fields['marketing_feedback'].clean('website'), self.choice
        )

    def test_feedback_display_preserves_other_and_legacy_extra(self):
        other = MarketingChoice.objects.get(tag='andere')
        order = OnlineOrder(marketing_feedback=other,
                            marketing_feedback_extra='Via vrienden')
        with translation.override('nl'):
            self.assertEqual(order.marketing_feedback_full,
                             'Andere...: Via vrienden')
            order.marketing_feedback = self.choice
            self.assertEqual(order.marketing_feedback_full,
                             'Onze website: Via vrienden')
        order.marketing_feedback = None
        self.assertEqual(order.marketing_feedback_full, 'Via vrienden')
        order.marketing_feedback_extra = None
        self.assertEqual(order.marketing_feedback_full, '')

    def test_used_choice_cannot_be_deleted(self):
        production = Production.objects.create(name='Concert', description='')
        performance = Performance.objects.create(production=production, date=now())
        OnlineOrder.objects.create(
            performance=performance, date=now(), first_name='Test',
            last_name='Customer', email='test@example.com', hash='test',
            newsletter_signup=False, marketing_feedback=self.choice
        )
        with self.assertRaises(ProtectedError):
            self.choice.delete()


class MarketingChoiceMigrationTests(TransactionTestCase):
    migrate_from = ('orchestra_ticketing', '0016_alter_onlineorder_marketing_feedback')
    migrate_to = ('orchestra_ticketing', '0017_dynamic_marketing_choices')

    def test_migration_preserves_all_existing_feedback(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        self.addCleanup(self.restore_latest_schema)
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Production = old_apps.get_model('orchestra_ticketing', 'Production')
        Performance = old_apps.get_model('orchestra_ticketing', 'Performance')
        OnlineOrder = old_apps.get_model('orchestra_ticketing', 'OnlineOrder')
        production = Production.objects.create(name='Migration concert',
                                               description='')
        performance = Performance.objects.create(production=production, date=now())
        tags = ['muzikant', 'flyer', 'dans_leuven', 'dans_herent', 'instagram',
                'facebook', 'nieuwsbrief', 'andere', 'legacy', '', None]
        order_ids = []
        for tag in tags:
            order = OnlineOrder.objects.create(
                performance=performance, date=now(), first_name='Test',
                last_name='Customer', email='test@example.com', hash='test',
                newsletter_signup=False, marketing_feedback=tag,
                marketing_feedback_extra='Existing information'
            )
            order_ids.append(order.pk)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        new_apps = executor.loader.project_state([self.migrate_to]).apps
        OnlineOrder = new_apps.get_model('orchestra_ticketing', 'OnlineOrder')
        MarketingChoice = new_apps.get_model('orchestra_ticketing', 'MarketingChoice')
        for order_id, tag in zip(order_ids, tags):
            order = OnlineOrder.objects.get(pk=order_id)
            self.assertEqual(order.marketing_feedback_id, tag)
            self.assertEqual(order.marketing_feedback_extra, 'Existing information')
            if tag is not None:
                self.assertEqual(order.marketing_feedback.tag, tag)
        self.assertEqual(MarketingChoice.objects.filter(active=True).count(), 8)
        self.assertEqual(MarketingChoice.objects.get(tag='andere').translation,
                         'Andere...')
        self.assertFalse(MarketingChoice.objects.get(tag='legacy').active)

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        OnlineOrder = old_apps.get_model('orchestra_ticketing', 'OnlineOrder')
        self.assertEqual(
            list(OnlineOrder.objects.order_by('pk').values_list(
                'marketing_feedback', flat=True)), tags
        )

    def restore_latest_schema(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_production_migration_assigns_choices_before_removing_active(self):
        target = ('orchestra_ticketing', '0018_production_marketing_choices')
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.addCleanup(self.restore_latest_schema)
        old_apps = executor.loader.project_state([self.migrate_to]).apps
        Production = old_apps.get_model('orchestra_ticketing', 'Production')
        MarketingChoice = old_apps.get_model('orchestra_ticketing', 'MarketingChoice')
        choice = MarketingChoice.objects.create(
            tag='website', text='Website', translation='Website', active=True
        )
        MarketingChoice.objects.create(
            tag='legacy', text='Legacy', translation='Legacy', active=False
        )
        production = Production.objects.create(name='Existing concert',
                                               description='')
        executor = MigrationExecutor(connection)
        executor.migrate([target])
        new_apps = executor.loader.project_state([target]).apps
        Production = new_apps.get_model('orchestra_ticketing', 'Production')
        MarketingChoice = new_apps.get_model('orchestra_ticketing', 'MarketingChoice')
        production = Production.objects.get(pk=production.pk)
        selected = production.marketing_choices.values_list('tag', flat=True)
        self.assertIn(choice.tag, selected)
        self.assertNotIn('legacy', selected)
        self.assertNotIn('active', [field.name for field in
                                   MarketingChoice._meta.get_fields()])
        new_production = Production.objects.create(name='New concert',
                                                   description='')
        self.assertFalse(new_production.marketing_choices.exists())
