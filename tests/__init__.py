import unittest
from .test_auth import TestAuthAPI
from .test_assets import TestAssetsAPI

suite_auth = unittest.TestLoader().loadTestsFromTestCase(TestAuthAPI)
suite_assets = unittest.TestLoader().loadTestsFromTestCase(TestAssetsAPI)
