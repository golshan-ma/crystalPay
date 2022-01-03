# crystal pay

crystalPay is a web3 django payment gateway project that can provide secure and fast payments

## setting up
1.set up virtual enviroment.

2.install requirements
```bash
pip install requirements.txt
```

3.set up database and connect it to project by crystalPay/settings.py

4.set up private key that should sign receipts by payments/constants.py

5.add configuration by admin panel.

## create a gateway

```python
import requests
import time
from web3.auto import w3
from eth_account.messages import encode_defunct
import secrets
from web3 import Web3
from eth_account import Account
import json
from django.urls import reverse

CONSTANT_PK = 'private key of gateway creator'
#metadata
msg = {
    
}

msg = json.dumps(msg)
massage = encode_defunct(text=msg)
signature = w3.eth.account.sign_message(massage, CONSTANT_PK)

sign = bytes.hex(signature['signature'])

data = {
    'config': 'tomo-test', #config slug
    'address': '',#address that assets will send to it
    'metadata': msg,
    'amount': 10,#amount of crypto currency
    'signature':sign,
    'callback':'https://callback.com' #url that user will redirect to after paying the gateway.
}
url = 'PROJECT_BASE_URL/payments/create'
requests.post(url, data)
```


## how its work:

1.the website who wants payment creating gateway by api and get gateway slug.

2.user will redirect to pay web page.(BASE_URL/payments/pay/gateway_slug)

3.user will send assets  to randomly generated wallet.

4.this app will check the balance of wallet. there are 3 possibilities

1. user paid exactly the amount should pay.
2. user paid more than it should pay.
3. user paid less than it should pay.

in 1st and 2nd case website will send assets to creator of gateway and refund extra assets to sender.

in 3rd case website will refund assets to sender.

main transaction fee will reduced from creator of gateway.

refund transaction fee will reduced from sender.

5.in the end website will sign the receipt and show it to user and then if user paid the amount will redirected to callback url.

6.creator can check the status of payment by api.(BASE_URL/payments/check/gateway_slug)



## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.



## License
[MIT](https://choosealicense.com/licenses/mit/)
