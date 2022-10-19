from textwrap import dedent

from moltin_tools import Product


def create_cart_message(products: [Product], total_price: str) -> str:
    """Create message with products in user's cart and total price"""
    message = ""
    for product in products:
        message += f"""
            Продукт: {product.name}
            Описание: {product.description}
            Количество: {product.amount}
            Цена: {product.price_amount * product.amount} {product.price_currency}
            
            """
    message += f"Общая цена: {total_price}"
    return dedent(message)


def create_product_description(product: Product) -> str:
    """Create message with product description"""
    message = f"""
        {product.name}
        {product.description}
        
        Цена: {product.price_amount} {product.price_currency}
        """
    return dedent(message)
