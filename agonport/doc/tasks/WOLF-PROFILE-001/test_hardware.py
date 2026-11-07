"""Offline dispatch refusal and producer/result identity checks; no device access."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
import hardware as h
import qualify_guest as q


class HardwareChecks(unittest.TestCase):
    def test_actual_producer_operands_and_no_mock(self):
        binding = json.loads((h.T / 'build/hardware-guest01/receipt.json').read_text())
        binding['source'] = str(Path(binding['guest']).parent)
        result = q.verify(binding)
        self.assertEqual(result['package_bytes'], 22572)
        self.assertEqual(len(result['operands']), 6)

    def boundary(self):
        # Test object only. Production requires ordinary verified construction.
        b = object.__new__(h.Bench)
        b.cleaning = False
        b.deadline = 1660
        b.observer_folder = None
        b.observer_record = {}
        return b

    def test_run_cannot_begin_inside_660_second_reserve(self):
        b = self.boundary()
        with patch.object(h.time, 'monotonic', return_value=1000), \
             patch.object(h.host_observer, 'check', return_value={}), \
             patch.object(h.h.Bench, 'line') as target:
            with self.assertRaises(h.BudgetStop):
                b.line(None, 'run', 'RUN .')
            target.assert_not_called()

    def test_observer_loss_blocks_successor_but_not_restore(self):
        b = self.boundary()
        with patch.object(h.host_observer, 'check', side_effect=h.host_observer.ObserverUnavailable('lost')), \
             patch.object(h.h.Bench, 'flash') as target:
            with self.assertRaises(h.host_observer.ObserverUnavailable):
                b.flash('b', 'candidate')
            target.assert_not_called()
            b.cleaning = True
            b.flash('restore', 'incoming')
            target.assert_called_once_with('restore', 'incoming')

    def test_no_handshake_means_no_entry(self):
        with tempfile.TemporaryDirectory() as directory:
            b = self.boundary()
            b.out = Path(directory)
            with patch.object(h.host_observer, 'wait', side_effect=h.host_observer.ObserverUnavailable('missing')), \
                 patch.object(b, 'entry') as entry:
                with self.assertRaises(h.host_observer.ObserverUnavailable):
                    b.suite()
                entry.assert_not_called()
            self.assertTrue(json.loads((b.out / 'failure.json').read_text())['no_automatic_replay'])

    def test_result_requires_real_count_stack_timer_and_identical_resident_report(self):
        binding = json.loads((h.T / 'build/hardware-guest01/receipt.json').read_text())
        binding['source'] = str(Path(binding['guest']).parent)
        ram = bytearray(Path(binding['guest']).read_bytes())
        done = bytearray(32)
        done[:4] = b'WPT1'
        done[8:11] = (250).to_bytes(3, 'little')
        for at in (12, 16):
            done[at:at+3] = (0xbff00).to_bytes(3, 'little')
        for at in (24, 28):
            done[at:at+4] = (4096).to_bytes(4, 'little')
        for label, value in (('wp_test_entry_sp', 0xbff00), ('wp_test_exit_sp', 0xbff00),
                             ('wp_sequence', 250), ('wp_dropped', 0)):
            at = q.address(binding, label)
            ram[at:at+3] = value.to_bytes(3, 'little')
        for label in ('wp_status', 'wp_owned', 'wp_count', 'wp_old_ctl'):
            ram[q.address(binding, label)] = 0
        at = q.address(binding, 'wp_test_report')
        ram[at:at+32] = done
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'ram.bin').write_bytes(ram)
            (folder / 'DONE.BIN').write_bytes(done)
            self.assertTrue(q.check_return(binding, folder)['passed'])
            for offset, value in ((4, 4), (8, 249), (16, 1), (24, 1), (7, 1)):
                bad = bytearray(done)
                bad[offset] = value
                (folder / 'DONE.BIN').write_bytes(bad)
                with self.subTest(offset=offset), self.assertRaises(AssertionError):
                    q.check_return(binding, folder)


if __name__ == '__main__':
    unittest.main()
