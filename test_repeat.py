from __future__ import unicode_literals

import io
import itertools
import subprocess
import sys
import textwrap

if sys.version_info >= (2, 7):
    import unittest
else:
    import unittest2 as unittest

if sys.version_info >= (3, 3):
    import unittest.mock as mock
else:
    import mock

import six

import repeat


class MockCheckCall(object):
    def __init__(self, returncodes=[]):
        self.returncodes = itertools.chain(returncodes, itertools.repeat(0))

    def __call__(self, cmd):
        return next(self.returncodes)


class TestRepeat(unittest.TestCase):
    """
    Tests for the 'repeat' function.

    """
    def setUp(self):
        self.mock_stdout = io.StringIO()
        self.mock_cmd = ['do', 'something']

    def tearDown(self):
        pass

    def test_repeat_ten_times(self):
        with mock.patch('repeat.subprocess.call') as m:
            m.side_effect = MockCheckCall()
            returncode = repeat.repeat(
                self.mock_cmd, count=10, progress_stream=self.mock_stdout)
        self.assertEqual(returncode, 0)
        self.assertEqual(m.call_count, 10)
        for args, kwargs in m.call_args_list:
            self.assertEqual(len(args), 1)
            self.assertEqual(args[0], self.mock_cmd)
            self.assertFalse(kwargs)

    def test_repeat_zero_times(self):
        with mock.patch('repeat.subprocess.call') as m:
            returncode = repeat.repeat(
                self.mock_cmd, count=0, progress_stream=self.mock_stdout)
        self.assertEqual(returncode, 0)
        self.assertFalse(m.called)

    def test_abort_on_failure(self):
        with mock.patch('repeat.subprocess.call') as m:
            m.side_effect = MockCheckCall(returncodes=[0, 7])
            returncode = repeat.repeat(
                self.mock_cmd, count=10, progress_stream=self.mock_stdout)
        self.assertEqual(returncode, 1)
        self.assertEqual(m.call_count, 2)

    def test_no_progress_output_when_verbose_is_false(self):
        with mock.patch('repeat.subprocess.call'):
            repeat.repeat(
                cmd=self.mock_cmd,
                count=10,
                verbose=False,
                progress_stream=self.mock_stdout,
            )
        output = self.mock_stdout.getvalue()
        self.assertEqual(output, '')

    def test_prefix_in_progress_output(self):
        prefix = 'test_prefix: '
        with mock.patch('repeat.subprocess.call') as m:
            m.side_effect = MockCheckCall()
            repeat.repeat(
                cmd=self.mock_cmd,
                count=10,
                verbose=True,
                progress_stream=self.mock_stdout,
                prefix=prefix,
            )
        output = self.mock_stdout.getvalue().splitlines(True)
        # There should be at least *some* output.
        self.assertGreater(len(output), 0)
        for line in output:
            self.assertTrue(line.startswith(prefix))
            self.assertTrue(line.endswith('\n'))

    def test_reported_runs_in_progress_output(self):
        with mock.patch('repeat.subprocess.call') as m:
            m.side_effect = MockCheckCall()
            repeat.repeat(
                cmd=self.mock_cmd,
                count=3,
                verbose=True,
                progress_stream=self.mock_stdout,
                prefix='testing:',
            )
        full_output = self.mock_stdout.getvalue()
        expected_run_reporting = textwrap.dedent("""\
            testing:Starting run 1 of 3.
            testing:Run 1 of 3 completed.
            testing:Starting run 2 of 3.
            testing:Run 2 of 3 completed.
            testing:Starting run 3 of 3.
            testing:Run 3 of 3 completed.
        """)
        self.assertIn(expected_run_reporting, full_output)

    def test_reported_runs_in_infinite_case(self):
        with mock.patch('repeat.subprocess.call') as m:
            m.side_effect = MockCheckCall(returncodes=[0, 0, -23])
            repeat.repeat(
                cmd=self.mock_cmd,
                count=None,
                verbose=True,
                progress_stream=self.mock_stdout,
                prefix='infinite testing> ',
            )
        full_output = self.mock_stdout.getvalue()
        expected_run_reporting = textwrap.dedent("""\
            infinite testing> Starting run 1.
            infinite testing> Run 1 completed.
            infinite testing> Starting run 2.
            infinite testing> Run 2 completed.
            infinite testing> Starting run 3.
            infinite testing> Run 3 failed with return code -23.
        """)
        self.assertIn(expected_run_reporting, full_output)
