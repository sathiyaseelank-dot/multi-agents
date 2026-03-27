import os
import unittest


class TestTxtTestCase(unittest.TestCase):
    def setUp(self):
        self.file_path = os.path.join(os.path.dirname(__file__), "..", "test.txt")

    def test_file_exists(self):
        self.assertTrue(os.path.exists(self.file_path), "test.txt does not exist")

    def test_file_content(self):
        with open(self.file_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "Hello", "test.txt content is not exactly 'Hello'")


if __name__ == "__main__":
    unittest.main()
