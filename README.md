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
