import unittest


class CITest(unittest.TestCase):
    def test_addition(self):
        self.assertEqual(2, 1+1)  # add assertion here


if __name__ == '__main__':
    unittest.main()
