# Official ticketing repo for both Alumni & Arenberg orchestra

This repo contains the code for the ticketing of both orchestra's located in Leuven.

## Settings

```python
settings.TICKETING_ENABLE_SELLER = true/false
settings.WEBSITE_BASE_URL = "http://address.be"
settings.TARGET_BANK_ACCOUNT
settings.EMAIL_WEBTEAM
settings.EMAIL_BESTUUR
```

## Marketing feedback

Marketing choices can be added and edited in Django admin. Each choice has a
unique, stable `tag`, an English `text`, and a Dutch `translation`. Labels follow
the current page language. Select the available choices per production using
`marketing_choices` in Django admin. The order form only offers that production's
selection. An empty selection offers
no marketing choices. Existing orders retain their choice, and referenced
choices cannot be deleted.
The tag is read-only in admin after creation because orders reference it.

Migration `0017_dynamic_marketing_choices` imports the eight original choices
and their Dutch translations without changing the tags stored on orders.
Additional legacy values (including empty strings) are retained as inactive
choices. Apply it with `python manage.py migrate`.

Migration `0018_production_marketing_choices` assigns the currently active
choices to all existing productions to preserve the options offered before this
change, then removes the `active` field from marketing choices. New productions
require an explicit selection in admin.

The existing tags `andere`, `muzikant`, `dans_leuven`, and `dans_herent` continue
to show the extra-information field. Displayed feedback and CSV exports include
any saved extra information alongside the translated choice.

## Todo

- Align both sides so that it is the same code and all references to one of the orchestra's is removed.
- Add payment QR code:
    # Use a EpcData instance to encapsulate the data of the European Payments Council Quick Response Code.
    epc_data = EpcData(
        name='Wikimedia Foerdergesellschaft',
        iban='DE33100205000001194700',
        amount=50.0,
        text='To Wikipedia'
    )
- Check mailing system
- Add a simplified login for scanners during the concert (f.ex. a qr code that redirects to the scanning page on one single day)
