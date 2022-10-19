from moltin_tools import Product


def create_cart_message(products: [Product], total_price: str) -> str:
    """Create message with products in user's cart and total price"""
    message = ""
    for product in products:
        message += f"Продукт: {product.name}\n" \
                   f"Описание: {product.description}\n" \
                   f"Количество: {product.amount}\n" \
                   f"Цена: {product.price_amount*product.amount} {product.price_currency}\n\n"
    message += f"Общая цена: {total_price}"
    return message


def create_product_description(product: Product) -> str:
    """Create message with product description"""
    message = f"{product.name}\n{product.description}\n\n" \
              f"Цена: {product.price_amount} {product.price_currency}"
    return message
