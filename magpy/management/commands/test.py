"""A test runner."""

import os
import sys
import imp
import unittest
import doctest
from importlib import import_module
from magpy.management import BaseCommand
from magpy.server.database import Database


class Command(BaseCommand):
    """Run the unit tests for all the test labels in the provided list."""
    help = ('Run the unit tests for the given test labels.')
    args = '[test_label ...]'

    def handle(self, *args, **kwargs):
        """
        Run the unit tests for all the test labels in the provided list.
        Labels must be of the form:
         - app,TestClass,test_method
            Run a single specific test method
         - app,TestClass
            Run all the test methods in a given class
         - app
            Search for doctests and unittests in the named application.

        When looking for tests, the test runner will look in the models and
        tests modules for the application.

        A list of 'extra' tests may also be provided; these tests
        will be added to the test suite.

        Returns the number of tests that failed.
        """

        if args:
            labels = args
        else:
            database = Database()
            labels = database.get_app_list()

        suite = self.get_suite(labels)

        verbosity = int(kwargs['verbosity'])
        failures = unittest.TextTestRunner(verbosity=verbosity).run(suite)
        if failures:
            sys.exit(bool(failures))

    def get_suite(self, args):
        """Put all the tests in a suite."""
        suite = unittest.TestSuite()
        for label in args:
            parts = label.split(',')
            app = parts[0]
            try:
                test_case = parts[1]
            except IndexError:
                test_case = None
            try:
                test_method = parts[2]
            except IndexError:
                test_method = None

            if test_case:
                suite.addTest(self.build_testcase(app, test_case, test_method))
            else:
                # Get all the tests in the app.
                try:
                    unittests, doctests = self.get_tests(app)
                except TypeError:
                    print "No test directory in", app
                    unittests = doctests = None
                if unittests:
                    suite.addTest(unittests)
                if doctests:
                    suite.addTest(doctests)
        return suite

    def get_tests(self, app):
        """Load unit and doctests in the tests module. If module has
        a suite() method, use it.
        Otherwise build the test suite ourselves."""
        test_module = self.get_test_module(app)
        if not test_module:
            return

        if hasattr(test_module, 'suite'):
            return (test_module.suite(), None)
        else:
            unittests = unittest.defaultTestLoader.loadTestsFromModule(
                test_module)

            # If the test module is a package, look for extra test modules
            absolute_test_module_location = os.path.abspath(
                os.path.dirname(
                    test_module.__file__))
            path = os.path.dirname(absolute_test_module_location)
            if not imp.find_module('tests', [path,])[0]:
                # The module is a package rather than a file
                loader = unittest.TestLoader()
                extra_tests = loader.discover(
                    absolute_test_module_location)
                unittests.addTest(extra_tests)
            try:
                doctests = doctest.DocTestSuite(test_module)
            except ValueError:
                # No doc tests in tests.py
                doctests = None
        return (unittests, doctests)

    def build_testcase(self, app, test_case, test_method):
        """Get test or tests based on a test_case
        and optional test_method."""
        test_module = self.get_test_module(app)
        if not test_module:
            return
        test_class = getattr(test_module, test_case, None)
        if test_class:
            if issubclass(test_class, unittest.TestCase):
                # We found a testclass
                if test_method:
                    return test_class(test_method)
                else:
                    try:
                        return unittest.TestLoader().loadTestsFromTestCase(
                            test_class)
                    except TypeError:
                        raise ValueError(
                            "Cannot find test case %s for app %s" % (test_case,
                                                                     app))
        # Unittest was not found, look for a doctest instead
        tests = []
        try:
            doctests = doctest.DocTestSuite(test_module)
            # Now iterate over the suite, looking for doctests whose name
            # matches the pattern that was given
            for test in doctests:
                if test.id() in (
                    'tests.%s' % test_case,
                    'tests.__test__.%s' % test_case):
                    tests.append(test)
        except ValueError:
            # No doctests found.
            pass

        # If no tests were found, then we were given a bad test label.
        if not tests:
            raise ValueError(
                "Cannot find test case %s for app %s" % (test_case,
                                                     app))

        # Construct a suite out of the tests that matched.
        return unittest.TestSuite(tests)

    @staticmethod
    def get_test_module(app):
        """Find the tests in the app"""
        test_module = '%s.tests' % app
        try:
            test_module = import_module(test_module)
        except ImportError:
            test_module = None
        return test_module
