from functools import partial

import requests
from geopy import distance

from moltin_tools import PizzaAddress


def fetch_coordinates(apikey: str, address: str) -> (float, float):
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection'][
        'featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return float(lat), float(lon)


def get_address_dist(pizza_address, user_address):
    pizza_location = (pizza_address.lat, pizza_address.lon)

    return distance.distance(pizza_location, user_address).meters


def get_min_dist(pizza_addresses, user_address) -> (PizzaAddress, int):
    get_address_dist_with_args = partial(get_address_dist,
                                         user_address=user_address)
    nearest_address = min(pizza_addresses, key=get_address_dist_with_args)
    dist_to_nearest_address = int(
        round(get_address_dist(nearest_address, user_address), 0))
    return nearest_address, dist_to_nearest_address
