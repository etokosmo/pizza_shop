from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple, List

import requests
from slugify import slugify

motlin_token, token_expires_timestamp = None, None


class MoltinFlow(NamedTuple):
    id: str
    slug: int


class Token(NamedTuple):
    access_token: str
    expires: int


@dataclass()
class Product:
    id: str
    name: str
    slug: str = None
    description: str = None
    image_url: str = None
    price_amount: str = None
    price_currency: str = 'RUB'
    amount: int = 0


@dataclass()
class PizzaAddress:
    address: str
    alias: str
    lat: str
    lon: str
    deliveryman_tg: str = None
    id: str = None


# @dataclass()
# class Product:
#     id: str
#     name: str
#     description: str = None
#     amount: int = None
#     price: str = None


def is_valid_token(token_expires_timestamp: int) -> bool:
    """Return whether token has expired"""
    now_datetime = datetime.now()
    token_expires_datetime = datetime.fromtimestamp(token_expires_timestamp)
    return now_datetime < token_expires_datetime


def get_motlin_access_token(motlin_client_id: str,
                            motlin_client_secret: str) -> str:
    """Return motlin access token"""
    global motlin_token, token_expires_timestamp
    if (motlin_token is None) or (not is_valid_token(token_expires_timestamp)):
        motlin_token, token_expires_timestamp = make_authorization(
            motlin_client_id, motlin_client_secret)
    return motlin_token


def make_authorization(motlin_client_id: str,
                       motlin_client_secret: str) -> Token:
    """Return created access_token and expires of token"""
    data = {
        'client_id': motlin_client_id,
        'client_secret': motlin_client_secret,
        'grant_type': 'client_credentials',
    }

    response = requests.post('https://api.moltin.com/oauth/access_token',
                             data=data)
    response.raise_for_status()
    authorization = response.json()
    return Token(access_token=authorization.get("access_token"),
                 expires=authorization.get("expires"))


def get_all_products(motlin_client_id: str,
                     motlin_client_secret: str) -> [Product]:
    """Return list if Product class with product's id and name"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    response = requests.get('https://api.moltin.com/v2/products',
                            headers=headers)
    response.raise_for_status()
    store = response.json().get("data")
    return [Product(product.get("id"),
                    product.get("name")) for product in store]


def get_product_by_id(product_id: str, motlin_client_id: str,
                      motlin_client_secret: str) -> Product:
    """Return product serialized dict from moltin"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    response = requests.get(f'https://api.moltin.com/v2/products/{product_id}',
                            headers=headers)
    response.raise_for_status()
    product = response.json().get("data")
    return Product(
        product.get("id"),
        product.get("name"),
        product.get("slug"),
        product.get("description"),
        product.get("relationships").get("main_image").get("data").get("id"),
        product.get('price')[0].get('amount'),
        product.get('price')[0].get('currency')
    )


def get_product_image_by_id(product_file_id: str, motlin_client_id: str,
                            motlin_client_secret: str) -> str:
    """Return href product's image from moltin"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)

    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    response = requests.get(
        f'https://api.moltin.com/v2/files/{product_file_id}',
        headers=headers)
    response.raise_for_status()
    return response.json().get("data").get("link").get("href")


def add_product_in_cart(product_id: str, amount: int, customer_id: int,
                        motlin_client_id: str,
                        motlin_client_secret: str) -> None:
    """Add product with his amount in user cart"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
        'Content-Type': 'application/json',
        'X-MOLTIN-CURRENCY': 'RUB'
    }

    json_data = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': amount,
        },
    }

    response = requests.post(
        f'https://api.moltin.com/v2/carts/{customer_id}/items',
        headers=headers,
        json=json_data)
    response.raise_for_status()


def get_cart_items(customer_id, motlin_client_id: str,
                   motlin_client_secret: str) -> ([Product], str):
    """Return list if Product class with products in cart and total price"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    response = requests.get(
        f'https://api.moltin.com/v2/carts/{customer_id}/items',
        headers=headers)
    response.raise_for_status()
    cart = response.json()
    products = [Product(product.get("id"),
                        product.get("name"),
                        product.get("slug"),
                        product.get("description"),
                        product.get("image").get("href"),
                        product.get('unit_price').get('amount'),
                        product.get('unit_price').get('currency'),
                        product.get('quantity')
                        ) for product in cart.get("data")]
    total_price = cart.get("meta").get("display_price").get("with_tax").get(
        "amount")
    return products, total_price


def remove_product_from_cart(product_id: str, customer_id: int,
                             motlin_client_id: str,
                             motlin_client_secret: str) -> None:
    """Remove product from user cart"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    response = requests.delete(
        f'https://api.moltin.com/v2/carts/{customer_id}/items/{product_id}',
        headers=headers)
    response.raise_for_status()


def create_customer(name: str, email: str, motlin_client_id: str,
                    motlin_client_secret: str) -> None:
    """Create customer"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    json_data = {
        'data': {
            'type': 'customer',
            'name': f'{name}',
            'email': f'{email}',
        },
    }
    response = requests.post('https://api.moltin.com/v2/customers',
                             headers=headers, json=json_data)
    response.raise_for_status()


def get_customer_by_id(customer_id: str, motlin_client_id: str,
                       motlin_client_secret: str) -> dict:
    """Get serialize dict with customer by id from motlin"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    response = requests.get(
        f'https://api.moltin.com/v2/customers/{customer_id}',
        headers=headers)
    response.raise_for_status()
    return response.json()


def add_product(product: Product, motlin_client_id: str,
                motlin_client_secret: str) -> None:
    """Upload product in Moltin"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }
    json_data = {
        'data': {
            'type': 'product',
            'name': product.name,
            'slug': product.slug,
            'sku': product.id,
            'description': product.description,
            'manage_stock': False,
            'price': [
                {
                    'amount': product.price_amount,
                    'currency': product.price_currency,
                    'includes_tax': True,
                },
            ],
            'status': 'live',
            'commodity_type': 'physical',
        },
    }

    response = requests.post('https://api.moltin.com/v2/products',
                             headers=headers, json=json_data)
    response.raise_for_status()
    product_id = response.json().get('data').get('id')
    uploaded_image_id = upload_image(product.image_url, motlin_client_id,
                                     motlin_client_secret)
    add_image_to_product(product_id, uploaded_image_id, motlin_client_id,
                         motlin_client_secret)


def upload_image(image_url: str, motlin_client_id: str,
                 motlin_client_secret: str) -> str:
    """Upload image on Motlin and Return image.id"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }
    files = {
        'file_location': (None, image_url),
    }

    response = requests.post('https://api.moltin.com/v2/files',
                             headers=headers, files=files)
    response.raise_for_status()
    image_id = response.json().get('data').get('id')
    return image_id


def add_image_to_product(product_id: str, image_id: str, motlin_client_id: str,
                         motlin_client_secret: str) -> None:
    """Add uploaded image to Product"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }
    json_data = {
        'data': {
            'type': 'main_image',
            'id': image_id,
        },
    }

    response = requests.post(
        f'https://api.moltin.com/v2/products/{product_id}/relationships/main-image',
        headers=headers, json=json_data)
    response.raise_for_status()


def create_flow(name: str, description: str, motlin_client_id: str,
                motlin_client_secret: str) -> MoltinFlow:
    """Create Flow and Return flow_id, flow_slug"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    json_data = {
        'data': {
            'type': 'flow',
            'name': name,
            'slug': slugify(name),
            'description': description,
            'enabled': True,
        },
    }

    response = requests.post('https://api.moltin.com/v2/flows',
                             headers=headers, json=json_data)
    response.raise_for_status()
    flow_id = response.json().get('data').get('id')
    flow_slug = response.json().get('data').get('slug')
    return MoltinFlow(id=flow_id, slug=flow_slug)


def create_field_in_flow(flow_id: str, field_name: str, description: str,
                         field_type: str, required: bool,
                         motlin_client_id: str,
                         motlin_client_secret: str) -> str:
    """Create field in flow and Return field_slug of this flow"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    json_data = {
        'data': {
            'type': 'field',
            'name': field_name,
            'slug': slugify(field_name),
            'field_type': field_type,
            'description': description,
            'required': required,
            'enabled': True,
            'relationships': {
                'flow': {
                    'data': {
                        'type': 'flow',
                        'id': flow_id,
                    },
                },
            },
        },
    }

    response = requests.post('https://api.moltin.com/v2/fields',
                             headers=headers, json=json_data)
    response.raise_for_status()
    return response.json().get('data').get('slug')


def create_an_entry(flow_slug: str,
                    address_field_slug: str, address_value: str,
                    alias_field_slug: str, alias_value: str,
                    lat_field_slug: str, lat_value: str,
                    lon_field_slug: str, lon_value: str,
                    motlin_client_id: str,
                    motlin_client_secret: str) -> None:
    """Create Pizza Address entry in fields in Flow-Address"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    json_data = {
        'data': {
            'type': 'entry',
            address_field_slug: address_value,
            alias_field_slug: alias_value,
            lat_field_slug: lat_value,
            lon_field_slug: lon_value,
        }
    }

    response = requests.post(
        f'https://api.moltin.com/v2/flows/{flow_slug}/entries',
        headers=headers,
        json=json_data)
    response.raise_for_status()


def create_customer_address(user: int, lat: float, lon: float, flow_slug: str,
                            motlin_client_id: str,
                            motlin_client_secret: str) -> None:
    """Create User-customer Address entry in fields in Flow-Customer"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    json_data = {
        'data': {
            'type': 'entry',
            'lat': lat,
            'lon': lon,
            'customer': user,
        }
    }

    response = requests.post(
        f'https://api.moltin.com/v2/flows/{flow_slug}/entries',
        headers=headers,
        json=json_data)
    response.raise_for_status()
    return response.json().get('data').get('id')


def get_all_address_entries(slug: str, motlin_client_id: str,
                            motlin_client_secret: str) -> List[PizzaAddress]:
    """Return all Pizza Address"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    response = requests.get(f'https://api.moltin.com/v2/flows/{slug}/entries',
                            headers=headers)
    response.raise_for_status()

    addresses = response.json().get('data')
    return [PizzaAddress(
        address=address.get('adres'),
        alias=address.get('alias'),
        lat=address.get('shirota'),
        lon=address.get('dolgota'),
        deliveryman_tg=address.get('deliveryman_tg'),
        id=address.get('id')
    ) for address in addresses]


def get_address_by_id(slug: str, id: str, motlin_client_id: str,
                      motlin_client_secret: str) -> PizzaAddress:
    """Return PizzaAddress class by address_id"""
    motlin_access_token = get_motlin_access_token(motlin_client_id,
                                                  motlin_client_secret)
    headers = {
        'Authorization': f'Bearer {motlin_access_token}',
    }

    response = requests.get(
        f'https://api.moltin.com/v2/flows/{slug}/entries/{id}',
        headers=headers)
    response.raise_for_status()

    address = response.json().get('data')
    return PizzaAddress(
        address=address.get('adres'),
        alias=address.get('alias'),
        lat=address.get('shirota'),
        lon=address.get('dolgota'),
        deliveryman_tg=address.get('deliveryman_tg'),
        id=address.get('id'))
