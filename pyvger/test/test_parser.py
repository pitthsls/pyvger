import unittest
from pyvger import parseholdings as ph


class TestCoverage(unittest.TestCase):
    def test_enum(self):
        enum = 'v.1-v.4:no.3'
        result = ph.parse_enum(enum)

        self.assertEqual(result['ec1'], 'v.')
        self.assertEqual(result['ec2'], 'no.')
        self.assertEqual(result['es1'], 1)
        self.assertEqual(result['ee1'], 4)
        self.assertEqual(result['es2'], 1)
        self.assertEqual(result['ee2'], 3)
