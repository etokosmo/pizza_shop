# Pizza Bot

## Goals

* Parse data about pizza and pizzerias
* Create a bot with inline buttons
* Connect Redis database
* Integrate with CMS
* Accept payments


## Bot example

You can see this project[here](https://t.me/etokosmo1337_bot).


![Пример результата для Telegram](https://dvmn.org/filer/canonical/1569216289/327/)


## Configurations

* Python version: 3.8.5
* Libraries: requirements.txt

## Launch

- Download code
- Through the console in the directory with the code, install the virtual environment with the command:
```bash
python3 -m venv env
```

- Activate the virtual environment with the command:
```bash
source env/bin/activate
```

- Install the libraries with the command:
```bash
pip install -r requirements.txt
```

- Write the environment variables in the `.env` file in the format KEY=VALUE


`TELEGRAM_API_TOKEN` Telegram token. Available from [BotFather](https://telegram.me/BotFather).

`TELEGRAM_CHAT_ID` Telegram chat ID where bot errors will be sent.

`DATABASE_HOST` Redis database address.

`DATABASE_PORT` Redis database port.

`DATABASE_PASSWORD` Redis database password.

`MOTLIN_CLIENT_ID` Client id on [motlin](https://euwest.cm.elasticpath.com/).

`MOTLIN_CLIENT_SECRET` Client server on [motlin](https://euwest.cm.elasticpath.com/).

`YANDEX_GEO_API_TOKEN` [Yandex geocoder API](https://developer.tech.yandex.ru/).

`TG_MERCHANT_TOKEN` Telegram Payment Token. Available from [BotFather](https://telegram.me/BotFather).

If you want parse data you need this variables:

`ADDRESSES_FILENAME` Filename of JSON Addresses data in current directory e.g. `shop/addresses.json`

`MENU_FILENAME` Filename of JSON Menu data in current directory e.g. `shop/menu.json`

- To launch a bot in Telegram, run the script with the command:
```bash
python3 tg_bot.py
```

- To parse data, run the script with the command:
```bash
python3 parse_tools.py
```

## Deploy

* Create `pizza_shop.service` in `/etc/systemd/system/`. Use `nano` or `vim`.

<details>
  <summary>pizza_shop.service</summary>

```
[Unit]
Description=Pizza - Telegram Bot
After=syslog.target
After=network.target

[Service]
Type=simple
WorkingDirectory=<FULL PATH TO YOU CODE>
ExecStart=<FULL PATH TO YOU CODE>/env/bin/python3 tg_bot.py
RestartSec=60
Restart=always

[Install]
WantedBy=multi-user.target
```

</details>

* Start bot with continuous work
```bash
sudo systemctl enable pizza_shop.service 
sudo systemctl start pizza_shop.service
```
* You can check status service
```bash
sudo systemctl enable pizza_shop.service 
```
* You can check logs
```bash
sudo journalctl -u  pizza_shop.service 
```

> The code is written for educational purposes - this is a lesson in the course on Python and web development on the site [Devman](https://dvmn.org).
