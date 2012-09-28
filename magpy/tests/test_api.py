"""Test api.py."""

from unittest import TestCase, main
from magpy.server.api import CommandHandler

class TestCommandHandler(TestCase):
    """Test advanced commands."""
    def test_create_unique_id_empty_list(self):
        self.assertEqual(
            CommandHandler._create_unique_id([], 'Lola'),
            'Lola_1')
    def test_create_unique_id_matching_item(self):
        self.assertEqual(
            CommandHandler._create_unique_id(['Lola_1'], 'Lola'),
            'Lola_2')
    def test_create_unique_two_matching_items(self):
        self.assertEqual(
            CommandHandler._create_unique_id(['Lola_1', 'Lola_2'], 'Lola'),
            'Lola_3')
    def test_create_unique_with_bad_input(self):
        self.assertRaises(
            ValueError,
            CommandHandler._create_unique_id,
            ['10001_1', '10001_2', '10003_2'], '10001')


if __name__ == '__main__':
    main()
