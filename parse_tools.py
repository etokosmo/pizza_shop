import json
import logging
from dataclasses import dataclass
from pathlib import Path

from environs import Env
from requests.exceptions import HTTPError
from slugify import slugify

from moltin_tools import add_product, Product, create_flow, \
    create_field_in_flow, PizzaAddress, create_an_entry, MoltinClient

BASE_DIR = Path(__file__).resolve(strict=True).parent
logger = logging.getLogger(__name__)


@dataclass()
class FlowFields:
    address_field: str
    alias_field: str
    lat_field: str
    lon_field: str


def parse_menu(path_to_menu: str, moltin_client: MoltinClient):
    with open(path_to_menu, "r", encoding='utf-8') as menu_file:
        menu_json = menu_file.read()

    menu = json.loads(menu_json)
    for dish in menu:
        product = Product(
            name=dish.get("name"),
            slug=slugify(dish.get("name")),
            id=str(dish.get("id")),
            description=dish.get("description"),
            image_url=dish.get("product_image").get("url"),
            price_amount=dish.get("price"),
            price_currency='RUB' if dish.get(
                "culture_name") == 'ru-RU' else "USD"
        )
        try:
            add_product(product, moltin_client)
        except HTTPError as error:
            logger.info(
                f"Product: {product.id} - {product.name}. An error occurred while loading product\n{error}")
        else:
            logger.info(
                f"Product: {product.id} - {product.name} uploaded successfully")


def parse_addresses(path_to_addresses: str, flow_fields: FlowFields,
                    flow_slug: str, moltin_client: MoltinClient):
    with open(path_to_addresses, "r", encoding='utf-8') as addresses_file:
        addresses_json = addresses_file.read()

    addresses = json.loads(addresses_json)
    for address in addresses:
        pizza_address = PizzaAddress(
            address=address.get("address").get("full"),
            alias=address.get("alias"),
            lat=address.get("coordinates").get("lat"),
            lon=address.get("coordinates").get("lon"),
        )
        try:
            create_an_entry(
                flow_slug,
                flow_fields.address_field, pizza_address.address,
                flow_fields.alias_field, pizza_address.alias,
                flow_fields.lat_field, pizza_address.lat,
                flow_fields.lon_field, pizza_address.lon,
                moltin_client)
        except HTTPError as error:
            logger.info(
                f"Address: {pizza_address.address}. An error occurred while loading address\n{error}")
        else:
            logger.info(
                f"Address: {pizza_address.address} uploaded successfully")


def main():
    logging.basicConfig(
        format='%(asctime)s : %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S',
        level=logging.INFO
    )
    env = Env()
    env.read_env()
    moltin_client = MoltinClient(
        client_id=env("MOTLIN_CLIENT_ID"),
        client_secret=env("MOTLIN_CLIENT_SECRET")
    )
    menu_filename = env("MENU_FILENAME")
    addresses_filename = env("ADDRESSES_FILENAME")

    path_to_menu = BASE_DIR / menu_filename
    path_to_addresses = BASE_DIR / addresses_filename
    flow_name = 'Pizza Address'
    flow_description = 'Адрес пиццерии'

    parse_menu(path_to_menu, moltin_client)

    flow_id, flow_slug = create_flow(flow_name, flow_description,
                                     moltin_client)
    address_field = create_field_in_flow(flow_id, 'address', flow_description,
                                      'string', True, moltin_client)
    alias_field = create_field_in_flow(flow_id, 'alias', 'Алиас пиццерии',
                                       'string', True, moltin_client)
    lat_field = create_field_in_flow(flow_id, 'lat', 'Широта пиццерии',
                                     'string', True, moltin_client)
    lon_field = create_field_in_flow(flow_id, 'lon', 'Долгота пиццерии',
                                     'string', True, moltin_client)

    flow_fields = FlowFields(
        address_field=address_field,
        alias_field=alias_field,
        lat_field=lat_field,
        lon_field=lon_field
    )
    parse_addresses(path_to_addresses, flow_fields, flow_slug, moltin_client)


if __name__ == "__main__":
    main()
