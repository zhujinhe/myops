#!/usr/bin/env python
import coverage
import unittest
from tests import suite_auth, suite_assets

COV = coverage.coverage(branch=True, include='app/*')
COV.start()

unittest.TextTestRunner(verbosity=2).run(suite_auth)
unittest.TextTestRunner(verbosity=2).run(suite_assets)

COV.stop()
COV.report()
