import logging
from functools import partial
from textwrap import dedent

import redis
from environs import Env
from notifiers.logging import NotificationHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, \
    LabeledPrice
from telegram.ext import CallbackQueryHandler, CommandHandler, \
    MessageHandler, Updater, Filters, CallbackContext, PreCheckoutQueryHandler

from format_message import create_cart_message, create_product_description
from geo_tools import fetch_coordinates, get_min_dist
from moltin_tools import get_all_products, get_product_by_id, \
    get_product_image_by_id, add_product_in_cart, get_cart_items, \
    remove_product_from_cart, create_customer, get_all_address_entries, \
    create_customer_address, MoltinClient

logger = logging.getLogger(__name__)


def send_notification(context):
    text = f"Приятного аппетита! *место для рекламы*\n\n" \
           f"*сообщение что делать если пицца не пришла*"
    context.bot.send_message(chat_id=context.job.context, text=text)


def create_menu_buttons(moltin_client: MoltinClient):
    products = get_all_products(moltin_client)
    keyboard = [
        [InlineKeyboardButton(product.name, callback_data=product.id)]
        for product in products]
    keyboard.append(
        [InlineKeyboardButton('Корзина', callback_data='cart')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def create_card_buttons(products):
    keyboard = [
        [InlineKeyboardButton(f"Убрать из корзины {product.name}",
                              callback_data=product.id)]
        for product in products]
    keyboard.append(
        [InlineKeyboardButton('В меню', callback_data='menu'),
         InlineKeyboardButton('Ввести адрес', callback_data='address')]
    )
    reply_markup = InlineKeyboardMarkup(keyboard)
    return reply_markup


def create_address_keyboard():
    keyboard = [[InlineKeyboardButton('В меню', callback_data='menu'),
                 InlineKeyboardButton('Ввести адрес',
                                      callback_data='address')]]
    return keyboard


def start(update: Update, context: CallbackContext, payment_token: str,
          moltin_client: MoltinClient, ya_geo_api_token: str):
    reply_markup = create_menu_buttons(moltin_client)

    update.message.reply_text('Please choose:', reply_markup=reply_markup)
    return "HANDLE_MENU"


def handle_menu(update: Update, context: CallbackContext, payment_token: str,
                moltin_client: MoltinClient, ya_geo_api_token: str):
    query = update.callback_query
    if query.data == 'cart':
        products, total_price = get_cart_items(update.effective_user.id,
                                               moltin_client)
        context.user_data['total_price'] = total_price
        message = create_cart_message(products, total_price)
        reply_markup = create_card_buttons(products)
        context.bot.send_message(text=message,
                                 reply_markup=reply_markup,
                                 chat_id=query.message.chat_id)
        return "HANDLE_CART"
    product = get_product_by_id(query.data, moltin_client)
    keyboard = [
        [InlineKeyboardButton("Добавить в корзину",
                              callback_data=f"1,{product.id}"), ],
        [InlineKeyboardButton("Назад", callback_data="back")],
        [InlineKeyboardButton('Корзина', callback_data='cart')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_photo(
        chat_id=query.message.chat_id,
        photo=get_product_image_by_id(product.image_url, moltin_client),
        caption=create_product_description(product),
        reply_markup=reply_markup
    )
    context.bot.delete_message(chat_id=query.message.chat_id,
                               message_id=query.message.message_id)
    return "HANDLE_DESCRIPTION"


def handle_cart(update: Update, context: CallbackContext, payment_token: str,
                moltin_client: MoltinClient, ya_geo_api_token: str):
    query = update.callback_query
    if query.data == 'menu':
        reply_markup = create_menu_buttons(moltin_client)

        context.bot.send_message(text='Please choose:',
                                 reply_markup=reply_markup,
                                 chat_id=query.message.chat_id)
        context.bot.delete_message(chat_id=query.message.chat_id,
                                   message_id=query.message.message_id)
        return "HANDLE_MENU"
    if query.data == 'email':
        context.bot.send_message(text="Напишите ваш email",
                                 chat_id=query.message.chat_id)
        return "HANDLE_WAITING_EMAIL"
    if query.data == 'address':
        context.bot.send_message(
            text="Пришлите ваш адрес текстом или геолокацию",
            chat_id=query.message.chat_id)
        return "HANDLE_WAITING_ADDRESS"
    else:
        remove_product_from_cart(query.data, update.effective_user.id,
                                 moltin_client)
        products, total_price = get_cart_items(update.effective_user.id,
                                               moltin_client)
        context.user_data['total_price'] = total_price
        message = create_cart_message(products, total_price)
        reply_markup = create_card_buttons(products)
        context.bot.send_message(text=message,
                                 reply_markup=reply_markup,
                                 chat_id=query.message.chat_id)
        return "HANDLE_CART"


def handle_description(update: Update, context: CallbackContext,
                       payment_token: str, moltin_client: MoltinClient,
                       ya_geo_api_token: str):
    query = update.callback_query
    try:
        command, product_id = query.data.split(",")
    except ValueError:
        command = query.data
        product_id = None

    if command == 'back':
        reply_markup = create_menu_buttons(moltin_client)

        context.bot.send_message(text='Please choose:',
                                 reply_markup=reply_markup,
                                 chat_id=query.message.chat_id)
        context.bot.delete_message(chat_id=query.message.chat_id,
                                   message_id=query.message.message_id)
        return "HANDLE_MENU"

    if command == 'cart':
        products, total_price = get_cart_items(update.effective_user.id,
                                               moltin_client)
        context.user_data['total_price'] = total_price
        message = create_cart_message(products, total_price)
        reply_markup = create_card_buttons(products)
        context.bot.send_message(text=message,
                                 reply_markup=reply_markup,
                                 chat_id=query.message.chat_id)
        return "HANDLE_CART"

    if command == '1':
        update.callback_query.answer("Товар добавлен в корзину")
        add_product_in_cart(product_id, 1, update.effective_user.id,
                            moltin_client)
        return "HANDLE_DESCRIPTION"
    if command == '3':
        update.callback_query.answer("Товар добавлен в корзину")
        add_product_in_cart(product_id, 3, update.effective_user.id,
                            moltin_client)
        return "HANDLE_DESCRIPTION"
    if command == '5':
        update.callback_query.answer("Товар добавлен в корзину")
        add_product_in_cart(product_id, 5, update.effective_user.id,
                            moltin_client)
        return "HANDLE_DESCRIPTION"
    return "HANDLE_MENU"


def handle_waiting_email(update: Update, context: CallbackContext,
                         payment_token: str, moltin_client: MoltinClient,
                         ya_geo_api_token: str):
    user = update.effective_user
    name = f"{user.first_name}_tgid-{user.id}"
    email = update.message.text
    create_customer(name, email, moltin_client)
    context.bot.send_message(
        text=f'Вы прислали мне эту почту: {email}',
        chat_id=update.message.chat_id)


def handle_waiting_address(update: Update, context: CallbackContext,
                           payment_token: str, moltin_client: MoltinClient,
                           ya_geo_api_token: str):
    query = update.callback_query
    if query:
        if query.data == 'menu':
            reply_markup = create_menu_buttons(moltin_client)

            context.bot.send_message(text='Please choose:',
                                     reply_markup=reply_markup,
                                     chat_id=query.message.chat_id)
            context.bot.delete_message(chat_id=query.message.chat_id,
                                       message_id=query.message.message_id)
            return "HANDLE_MENU"
        if query.data == 'address':
            context.bot.send_message(
                text="Пришлите ваш адрес текстом или геолокацию",
                chat_id=query.message.chat_id)
            return "HANDLE_WAITING_ADDRESS"

    if update.edited_message:
        message = update.edited_message
    else:
        message = update.message
    if message.location:
        current_pos = (message.location.latitude, message.location.longitude)
    else:
        current_pos = fetch_coordinates(ya_geo_api_token, message.text)
        if not current_pos:
            keyboard = create_address_keyboard()
            reply_markup = InlineKeyboardMarkup(keyboard)
            context.bot.send_message(
                text=f'Не смогли разобрать ваш адрес, введите еще раз',
                reply_markup=reply_markup,
                chat_id=update.message.chat_id)
            return "HANDLE_WAITING_ADDRESS"

    addresses = get_all_address_entries('pizza-address', moltin_client)
    nearest_address, dist_to_nearest_address = get_min_dist(addresses,
                                                            current_pos)

    if dist_to_nearest_address <= 500:
        message = f'''
            Может заберете пиццу из нашей пиццерии неподалёку?
            Она всего в {dist_to_nearest_address} метрах от вас!
            Вот её адрес: {nearest_address.address}.
            А можем и бесплатно доставить, нам не сложно :)
            '''
        keyboard = create_address_keyboard()
        keyboard.append(
            [InlineKeyboardButton('Доставка', callback_data='delivery'),
             InlineKeyboardButton('Самовывоз', callback_data='pickup')]
        )
    elif dist_to_nearest_address <= 5000:
        message = f'''
            Похоже придется ехать до вас на самокате.
            Доставка будет стоить 100 рублей.
            Доставляем или самовывоз?
            '''
        keyboard = create_address_keyboard()
        keyboard.append(
            [InlineKeyboardButton('Доставка', callback_data='delivery'),
             InlineKeyboardButton('Самовывоз', callback_data='pickup')]
        )
    elif dist_to_nearest_address <= 20000:
        message = f'''
            Похоже придется ехать до вас на машине.
            Доставка будет стоить 300 рублей.
            Доставляем или самовывоз?
            '''
        keyboard = create_address_keyboard()
        keyboard.append(
            [InlineKeyboardButton('Доставка', callback_data='delivery'),
             InlineKeyboardButton('Самовывоз', callback_data='pickup')]
        )
    else:
        message = f'''
            Простите, но так далеко мы пиццу не доставляем.
            Может заберете пиццу из нашей пиццерии?
            Ближайшая к вам всего в {dist_to_nearest_address} метрах от вас!
            Вот её адрес: {nearest_address.address}.
            '''
        keyboard = create_address_keyboard()
        keyboard.append(
            [InlineKeyboardButton('Доставка', callback_data='delivery')]
        )

    context.user_data['address'] = nearest_address.address
    context.user_data['deliveryman_tg'] = nearest_address.deliveryman_tg
    context.user_data['user_lat'] = current_pos[0]
    context.user_data['user_lon'] = current_pos[1]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(
        text=dedent(message),
        reply_markup=reply_markup,
        chat_id=update.message.chat_id)
    return "HANDLE_WAITING_DELIVERY"


def handle_delivery(update: Update, context: CallbackContext,
                    payment_token: str, moltin_client: MoltinClient,
                    ya_geo_api_token: str):
    query = update.callback_query
    if query.data == 'menu':
        reply_markup = create_menu_buttons(moltin_client)

        context.bot.send_message(text='Please choose:',
                                 reply_markup=reply_markup,
                                 chat_id=query.message.chat_id)
        context.bot.delete_message(chat_id=query.message.chat_id,
                                   message_id=query.message.message_id)
        return "HANDLE_MENU"
    if query.data == 'address':
        context.bot.send_message(
            text="Пришлите ваш адрес текстом или геолокацию",
            chat_id=query.message.chat_id)
        return "HANDLE_WAITING_ADDRESS"
    if query.data == 'delivery':
        deliveryman_tg = context.user_data['deliveryman_tg']
        user_lat = context.user_data['user_lat']
        user_lon = context.user_data['user_lon']
        user = update.effective_user
        create_customer_address(
            user=user.id,
            lat=user_lat,
            lon=user_lon,
            flow_slug='customer-address',
            moltin_client=moltin_client,
        )
        products, total_price = get_cart_items(update.effective_user.id,
                                               moltin_client)
        context.user_data['total_price'] = total_price
        message = create_cart_message(products, total_price)

        context.bot.send_message(text=message,
                                 chat_id=deliveryman_tg)
        context.bot.send_location(chat_id=deliveryman_tg,
                                  latitude=user_lat,
                                  longitude=user_lon)
        context.bot.send_message(text=f"Оплатите ваш заказ",
                                 chat_id=query.message.chat_id)

        chat_id = query.message.chat_id
        title = 'Оплатить'
        description = 'Оплатить заказ'
        payload = 'Payload'
        provider_token = payment_token
        start_parameter = 'test-payment'
        currency = 'RUB'
        price = context.user_data['total_price']
        prices = [LabeledPrice('Оплата', price * 100)]

        context.bot.sendInvoice(chat_id, title, description, payload,
                                provider_token, currency, prices,
                                start_parameter)
        return 'START'
    if query.data == 'pickup':
        address = context.user_data['address']
        context.bot.send_message(text=f"Ждем вас по адресу: {address}",
                                 chat_id=query.message.chat_id)
        return "HANDLE_MENU"


def precheckout_callback(update, context):
    query = update.pre_checkout_query
    if query.invoice_payload != 'Payload':
        context.bot.answer_pre_checkout_query(
            pre_checkout_query_id=query.id,
            ok=False,
            error_message='Что-то пошло не так и не туда...'
        )
    else:
        context.bot.answer_pre_checkout_query(
            pre_checkout_query_id=query.id,
            ok=True
        )


def successful_payment_callback(update, context):
    update.message.reply_text("Thank you for your payment!")
    update.message.reply_text("Ваш заказ создан")
    context.job_queue.run_once(send_notification, 3600,
                               context=update.effective_user.id)


def handle_users_reply(update: Update, context: CallbackContext,
                       redis_db: redis.client.Redis,
                       payment_token: str, moltin_client: MoltinClient,
                       ya_geo_api_token: str):
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = redis_db.get(str(chat_id)).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'HANDLE_WAITING_EMAIL': handle_waiting_email,
        'HANDLE_WAITING_ADDRESS': handle_waiting_address,
        'HANDLE_WAITING_DELIVERY': handle_delivery,
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context, payment_token,
                                   moltin_client, ya_geo_api_token)
        redis_db.set(str(chat_id), next_state)
    except Exception as err:
        logging.error(err)


def handle_error(update: Update, context: CallbackContext):
    """Log Errors caused by Updates."""
    logger.exception(context.error)


def main():
    logging.basicConfig(
        format='%(asctime)s : %(message)s',
        datefmt='%d/%m/%Y %H:%M:%S',
        level=logging.INFO
    )
    env = Env()
    env.read_env()
    telegram_api_token = env("TELEGRAM_API_TOKEN")
    telegram_chat_id = env("TELEGRAM_CHAT_ID")
    redis_database = redis.Redis(
        host=env("DATABASE_HOST"),
        port=env("DATABASE_PORT"),
        password=env("DATABASE_PASSWORD")
    )
    moltin_client = MoltinClient(
        client_id=env("MOTLIN_CLIENT_ID"),
        client_secret=env("MOTLIN_CLIENT_SECRET")
    )
    yandex_geo_api_token = env("YANDEX_GEO_API_TOKEN")
    tg_merchant_token = env.str("TG_MERCHANT_TOKEN")

    params = {
        'token': telegram_api_token,
        'chat_id': telegram_chat_id
    }
    tg_handler = NotificationHandler("telegram", defaults=params)
    logger.addHandler(tg_handler)

    updater = Updater(telegram_api_token)
    dispatcher = updater.dispatcher
    handle_users_reply_with_args = partial(
        handle_users_reply,
        redis_db=redis_database,
        payment_token=tg_merchant_token,
        moltin_client=moltin_client,
        ya_geo_api_token=yandex_geo_api_token
    )
    dispatcher.add_handler(
        CommandHandler('start', handle_users_reply_with_args))

    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply_with_args))
    dispatcher.add_handler(
        MessageHandler(Filters.text, handle_users_reply_with_args))
    dispatcher.add_error_handler(handle_error)
    handle_waiting_address_with_args = partial(
        handle_waiting_address,
        ya_geo_api_token=yandex_geo_api_token
    )
    location_handler = MessageHandler(Filters.location | Filters.text,
                                      handle_waiting_address_with_args)
    dispatcher.add_handler(location_handler)
    dispatcher.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    dispatcher.add_handler(MessageHandler(Filters.successful_payment,
                                          successful_payment_callback))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
