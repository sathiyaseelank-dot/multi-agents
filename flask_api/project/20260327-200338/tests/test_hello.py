import os
import unittest


class HelloFileTestCase(unittest.TestCase):
    def setUp(self):
        self.file_path = os.path.join(os.path.dirname(__file__), "..", "backend", "hello.txt")

    def test_hello_file_exists(self):
        self.assertTrue(os.path.exists(self.file_path), "hello.txt does not exist")

    def test_hello_file_content(self):
        with open(self.file_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "Hello World")


if __name__ == "__main__":
    unittest.main()
