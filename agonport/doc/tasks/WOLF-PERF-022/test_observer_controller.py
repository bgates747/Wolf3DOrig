"""Actual controller refuses unobserved submissions; cleanup cannot be trapped."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import hardware02 as h
from test_hardware02 import Model


class ObserverControllerTests(unittest.TestCase):
    def controller(self):
        b = object.__new__(h.Bench)
        b.cleaning = False
        b.deadline = 10000
        b.observer_folder = None
        b.observer_record = {}
        return b

    def test_loss_refuses_each_submission_before_inherited_io(self):
        b = self.controller()
        for name, args in (('line', (None, 'run', 'RUN .')),
                           ('transfer', (None, 'get', 'get', 'remote', 'local')),
                           ('metadata', (None, 'session')),
                           ('flash', ('b', 'image')),
                           ('probe', ('entry',)),
                           ('case', (1, 'vdplet', 'room'))):
            with self.subTest(name=name), patch.object(h.host_observer, 'check', side_effect=h.host_observer.ObserverUnavailable('lost')), patch.object(h.h.Bench, name) as submit:
                with self.assertRaises(h.host_observer.ObserverUnavailable):
                    getattr(b, name)(*args)
                submit.assert_not_called()

    def test_completed_transfer_then_observer_loss_refuses_successor(self):
        b = self.controller()
        with patch.object(h.time, 'monotonic', return_value=1000), patch.object(h.host_observer, 'check', side_effect=[{}, h.host_observer.ObserverUnavailable('lost')]), patch.object(h.h.Bench, 'transfer', return_value='original-job-finished') as submit:
            self.assertEqual(b.transfer(None, 'one', 'get', 'remote', 'local'), 'original-job-finished')
            with self.assertRaises(h.host_observer.ObserverUnavailable):
                b.transfer(None, 'two', 'get', 'remote', 'local')
            self.assertEqual(submit.call_count, 1)

    def test_cleanup_exempt_even_with_no_observer_and_expired_deadline(self):
        b = self.controller()
        b.cleaning = True
        b.deadline = -1
        with patch.object(h.host_observer, 'check', side_effect=AssertionError('must not check')) as check, patch.object(h.h.Bench, 'flash') as submit:
            b.flash('restore', 'exact-incoming')
            submit.assert_called_once_with('restore', 'exact-incoming')
            check.assert_not_called()

    def test_missing_handshake_refuses_entry_before_device_io(self):
        with tempfile.TemporaryDirectory() as folder:
            b = Model(folder)
            deadline = b.deadline
            with patch.object(h.host_observer, 'wait', side_effect=h.host_observer.ObserverUnavailable('missing')):
                with self.assertRaises(h.host_observer.ObserverUnavailable): b.suite()
            self.assertEqual(b.events, [])
            self.assertEqual(b.deadline, deadline)
            self.assertTrue((Path(folder) / 'failure.json').exists())

    def test_handshake_does_not_extend_absolute_dispatch_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            b = Model(folder)
            b.deadline = 1660
            with patch.object(h.time, 'monotonic', return_value=1000), patch.object(h.host_observer, 'wait', return_value={}), patch.object(h.host_observer, 'check', return_value={}):
                with self.assertRaises(h.BudgetStop): b.suite()
            self.assertEqual(b.deadline, 1660)
            self.assertNotIn(('module', 1, 'original'), b.events)


if __name__ == '__main__':
    unittest.main()
