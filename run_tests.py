#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test runner for Sharinbai tests
"""

import sys
import unittest


def run_tests():
    """Discover and run all tests in the tests directory"""
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover('tests')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1) 