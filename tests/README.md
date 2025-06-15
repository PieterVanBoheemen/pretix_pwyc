# Tests for pretix-pwyc

This directory contains the tests for the pretix Pay What You Can plugin.

## Running Tests

To run the tests, you need to have a working pretix development setup. Follow the instructions in the [pretix documentation](https://docs.pretix.eu/en/latest/development/setup.html) to set up your development environment.

Then run:

```bash
cd /path/to/pretix
python -m pytest tests/
```

## Test Structure

- `test_pwyc.py`: Tests basic functionality of the PWYC plugin
