# pretix Pay What You Can

A plugin for [pretix](https://github.com/pretix/pretix) that allows customers to choose their own price for tickets.

## Features

- Allow organizers to enable "Pay What You Can" pricing for specific items
- Set optional minimum prices
- Set suggested amounts
- Show custom explanation text to customers
- Works with all existing payment providers

## Installation

1. Download and install the plugin:

```bash
pip install pretix-pwyc
```

2. Enable the plugin in pretix:

```bash
python -m pretix plugins enable pretix_pwyc
```

3. Restart your pretix instance.

## Configuration

1. Go to your event settings
2. Enable the "Pay What You Can" plugin
3. Edit a product/item and enable "Pay What You Can" pricing
4. Configure minimum and suggested prices as needed

## License

This project is licensed under the Apache License 2.0.

## Security

If you discover any security-related issues, please email mail@pietervanboheemen.nl instead of using the issue tracker.
