import json
from pprint import pprint

# with open("shop/menu.json", "r", encoding='utf-8') as menu_file:
#     menu_json = menu_file.read()
#
# menu = json.loads(menu_json)
# pprint(menu)

with open("shop/addresses.json", "r", encoding='utf-8') as addresses_file:
    addresses_json = addresses_file.read()

addresses = json.loads(addresses_json)
pprint(addresses)

# title = 'Цыпленок барбекю'
#
# from slugify import slugify
#
# r = slugify(title)
# print(r)