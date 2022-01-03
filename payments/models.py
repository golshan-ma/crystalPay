import time
from django.db import models
from django.utils.text import slugify
import string
import random
from web3.auto import w3
from eth_account.messages import encode_defunct
import secrets
from web3 import Web3
from eth_account import Account
import json
from django.urls import reverse
import datetime
import constatns

# Create your models here.



class Configuration(models.Model):
    title = models.CharField(
        max_length=64,
        null=False,
        blank=False,
    )
    endpoint = models.URLField(
        max_length=128,
        null=False,
        blank=False
    )
    slug = models.SlugField(
        max_length=80,
        blank=True,
        null=False
    )
    is_available = models.BooleanField(
        blank=False,
        null=False,
        default=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def w3_connection(self):
        """
        this function create web3 connection.
        :return: web3 connection (web3)
        """
        conn = Web3(Web3.HTTPProvider(self.endpoint))
        return conn

    def __str__(self):
        return f'{self.slug}:{self.endpoint}'

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super(Configuration, self).save(*args, **kwargs)


class Gateway(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    config = models.ForeignKey(
        'Configuration',
        on_delete=models.PROTECT,
        null=False,
        blank=False
    )
    amount = models.FloatField(
        blank=False,
        null=False,
        default=0
    )
    paid_amount = models.FloatField(
        blank=False,
        null=False,
        default=0
    )
    creator_address = models.CharField(
        max_length=128,
        blank=False,
        null=False,
    )

    refund_address = models.CharField(
        max_length=128,
        blank=True,
        null=False,
        default='0'
    )
    signature = models.CharField(
        max_length=150,
        blank=False,
        null=False,
    )
    signature_public_key = models.CharField(
        max_length=150,
        blank=True,
        null=False,
    )
    metadata = models.CharField(
        max_length=512,
        blank=False,
        null=False,
    )
    is_paid = models.BooleanField(
        blank=False,
        null=False,
        default=False,
    )
    is_refunded = models.BooleanField(
        blank=False,
        null=False,
        default=False,
    )
    is_expired = models.BooleanField(
        blank=False,
        null=False,
        default=False,
    )
    private_key = models.CharField(
        max_length=128,
        blank=True,
        null=False,
        default='private-key'
    )
    main_tx_hash = models.CharField(
        max_length=150,
        blank=True,
        null=False,
        default='0'
    )
    refund_tx_hash = models.CharField(
        max_length=150,
        blank=True,
        null=False,
        default='0'
    )
    slug = models.SlugField(
        null=False,
        blank=True,
        unique=True
    )
    third_party_signature = models.CharField(
        max_length=300,
        blank=True,
        null=True,
    )
    callback_url = models.CharField(
        max_length=128,
        blank=True,
        null=False,
        default='0'
    )

    def __str__(self):
        return f'id:{self.slug}/{self.amount} to {self.creator_address}/sign : {self.signature}'

    def get_signature_public_key(self):
        """
        this function recover signature of gateway.
        :return: public key that sign gateway metadata. (str)
        """
        try:
            massage = self.metadata
            massage = encode_defunct(text=massage)
            signer_address = w3.eth.account.recover_message(massage, signature=self.signature)
            return signer_address
        except:
            return 'not valid signature'

    def get_public_key(self):
        """
        this function calculate public key of gateway.
        :return: public key (str)
        """
        if self.private_key and self.private_key != 'private-key':
            acct = Account.from_key(self.private_key)
            return acct.address
        else:
            return None

    def update_balance(self):
        """
        this function returns balance of gateway.
        :return: gateways balance (float)
        """
        if self.get_public_key():
            wei = self.config.w3_connection().eth.get_balance(self.get_public_key())
            return self.config.w3_connection().fromWei(wei, 'ether')

    def update_paid_amount(self):
        """
        this function update balance in db.
        :return:
        """
        self.paid_amount = self.update_balance()
        self.save()

    def expiration_datetime(self):
        """
        this function returns datetime of gateway expiration
        :return: datetime (str)
        """
        timestamp = self.created_at.timestamp()
        ts = timestamp + EXPIRATION
        n = datetime.datetime.utcfromtimestamp(ts).strftime('%b %d,%Y %H:%M:%S UTC')
        return n

    def get_metadata(self):
        """

        :return: dict form of gateway metadata.
        """
        return json.loads(self.metadata)

    def get_absolute_confirm_url(self):
        return reverse('confirm-payment-url', args=[self.slug])

    def calculate_gas_price(self):
        return self.config.w3_connection().eth.gasPrice

    def check_transaction(self):
        self.update_paid_amount()
        if self.paid_amount >= self.amount:
            return True
        else:
            return False

    def check_validity(self):
        '''
        checks that gateway is expired or not
        :return:
        '''
        current_utc = time.time()
        timestamp = self.created_at.timestamp()
        expiration_utc = timestamp + EXPIRATION
        if current_utc > expiration_utc:
            self.is_expired = True
            self.save()

    def width_percent(self):
        """

        :return: return percentage of paid amount
        """
        percent = float(self.paid_amount)/float(self.amount)*100
        stri = f'{percent}%'
        return stri

    def execute_transaction(self):
        self.update_paid_amount()
        gas_price = self.calculate_gas_price()
        transaction_fee = gas_price * GAS_LIMIT
        nonce = self.config.w3_connection().eth.get_transaction_count(self.get_public_key(), 'latest')
        paid_wei = self.config.w3_connection().toWei(self.paid_amount, 'ether')
        amount_wei = self.config.w3_connection().toWei(self.amount, 'ether')
        if self.paid_amount >= self.amount:
            value = amount_wei - transaction_fee
            main_tx = {
                'nonce': nonce,
                'to': self.creator_address,
                'value': value,
                'gas': GAS_LIMIT,
                'gasPrice': gas_price,
            }
            signed_tx = self.config.w3_connection().eth.account.sign_transaction(main_tx, self.private_key)
            tx_hash = self.config.w3_connection().eth.sendRawTransaction(signed_tx.rawTransaction)
            self.main_tx_hash = self.config.w3_connection().toHex(tx_hash)
            self.is_paid = True
            self.save()
            time.sleep(30)
            if paid_wei - amount_wei - transaction_fee > 0:
                refund_value = paid_wei - amount_wei - transaction_fee
                nonce = self.config.w3_connection().eth.get_transaction_count(self.get_public_key(), 'latest')
                refund_tx = {
                    'nonce': nonce,
                    'to': self.refund_address,
                    'value': refund_value,
                    'gas': GAS_LIMIT,
                    'gasPrice': gas_price,
                }
                signed_tx = self.config.w3_connection().eth.account.sign_transaction(refund_tx, self.private_key)
                tx_hash = self.config.w3_connection().eth.sendRawTransaction(signed_tx.rawTransaction)
                self.refund_tx_hash = self.config.w3_connection().toHex(tx_hash)
                self.is_refunded = True
                self.save()
        elif paid_wei - transaction_fee > 0:
            refund_value = paid_wei - transaction_fee
            nonce = self.config.w3_connection().eth.get_transaction_count(self.get_public_key(), 'latest')
            refund_tx = {
                'nonce': nonce,
                'to': self.refund_address,
                'value': refund_value,
                'gas': GAS_LIMIT,
                'gasPrice': gas_price,
            }
            signed_tx = self.config.w3_connection().eth.account.sign_transaction(refund_tx, self.private_key)
            tx_hash = self.config.w3_connection().eth.sendRawTransaction(signed_tx.rawTransaction)
            self.refund_tx_hash = self.config.w3_connection().toHex(tx_hash)
            self.is_refunded = True
        self.save()

    def sign_receipt(self):
        """
        this function sign the receipt of gateway
        :return:
        """
        msg = {
            'timestamp': self.created_at.timestamp(),
            'amount': self.amount,
            'target_address': self.creator_address,
            'refund_address': self.refund_address,
            'signature': self.signature,
            'signer': self.signature_public_key,
            'network': self.config.title,
            'main_tx_hash': self.main_tx_hash,
            'refund_tx_hash': self.refund_tx_hash,
            'is_paid': self.is_paid,
            'refund': self.is_refunded,
            'metadata': self.get_metadata(),
        }
        massage = encode_defunct(text=json.dumps(msg))
        signature = w3.eth.account.sign_message(massage, CONSTANT_PK)
        sign = bytes.hex(signature['signature'])
        self.third_party_signature = sign
        self.save()
        receipt = {
            'message': msg,
            'signature': sign
        }
        return receipt

    def save(self, *args, **kwargs):
        self.signature_public_key = self.get_signature_public_key()
        if not self.slug:
            self.slug = generate_slug(Gateway, SLUG_LENGTH)
        if not self.private_key or self.private_key == 'private-key':
            self.private_key = generate_private_key(Gateway)
        super(Gateway, self).save(*args, **kwargs)


def generate_slug(klass, slug_length):
    slug = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=slug_length))
    if klass.objects.filter(slug=slug):
        slug = generate_slug(klass, slug_length)
    return slug


def generate_private_key(klass):
    private = secrets.token_hex(32)
    private_key = "0x" + private
    if klass.objects.filter(private_key=private_key):
        private_key = generate_private_key(klass)
    return private_key
