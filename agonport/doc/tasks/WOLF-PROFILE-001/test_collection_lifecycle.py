"""Actual collector/client journals across intentional listener incarnations.

Only wire/status and physical I/O are local fakes; use the real persistent
metadata client, collector, raw-state and route methods and preserved105 data.
No device, network, emulator or lease operation is performed.
"""
from pathlib import Path
import json
import shutil
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch
import hardware as h
from sdcard import RemoteError


class CollectionLifecycle(unittest.TestCase):
    def exercise(self, old_final_label):
        original = h.T / 'build/hardware02'
        kit = json.loads((original / 'kit.json').read_text())
        actual = original / 'evidence/full-game'
        world = dict(boot=1, online=True, exits=0)

        def status(client):
            return dict(protocol=2, boot=world['boot'], online=world['online'])

        def exchange(client, request):
            operation = request[12]
            if operation == 1:
                return 0, struct.pack('<IHH', world['boot'], 212, 0x7f)
            if operation == 3:  # empty directory, so no removal is needed
                return 0, struct.pack('<IB', 0, 1)
            if operation == 11:
                world['online'] = False
                world['exits'] += 1
                return 0, b''
            raise AssertionError(('Unexpected wire operation', operation))

        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            shutil.copyfile(actual / 'ram.bin', folder / 'ram.bin')
            # Test object only; production always uses the verified constructor.
            bench = object.__new__(h.Bench)
            bench.url = 'http://test.invalid'
            bench.remote = kit['remote']
            bench.kit = kit
            bench.cleaning = True
            bench.own = Mock()
            bench.save_guest_ram = Mock()

            def transfer(where, label, operation, remote, local):
                self.assertEqual(operation, 'get')
                name = remote.rsplit('/', 1)[-1]
                if name in ('DONE.BIN', 'WOLFPROF.BIN'):
                    shutil.copyfile(actual / name, local)
                elif name == 'post-callback.bin':
                    Path(local).write_bytes(bytes(3))
                elif name in ('post-mode.bin', 'route.bin'):
                    Path(local).write_bytes(b'\0')
                else:
                    self.fail(('Unexpected transfer', remote))

            def line(where, label, command):
                self.assertTrue(command.startswith('EXEC '))
                self.assertFalse(world['online'])
                world['boot'] += 1
                world['online'] = True

            bench.transfer = transfer
            bench.line = line
            bench.wait_online = lambda wanted: self.assertEqual(world['online'], wanted)
            if old_final_label:
                normal_exit = bench.exit
                bench.exit = lambda where, label: normal_exit(where,
                    'post-exit' if label == 'profile-collection-exit' else label)

            client = h.h.m.Metadata
            with patch.object(client, 'status', status), patch.object(client, 'exchange', exchange):
                if old_final_label:
                    with self.assertRaisesRegex(RemoteError, 'Service restarted'):
                        bench.collect_profile(folder)
                    self.assertTrue(world['online'])
                    self.assertEqual(world['exits'], 2)
                    self.assertFalse((folder / 'receipt.json').exists())
                else:
                    bench.collect_profile(folder)
                    self.assertFalse(world['online'])
                    self.assertEqual(world['exits'], 3)
                    self.assertTrue(json.loads((folder / 'receipt.json').read_text())['passed'])
                # The completed earlier incarnation remains in its own journal.
                journal = json.loads((folder / 'post-exit-metadata.json').read_text())
                self.assertEqual(journal['boot'], 1)
                self.assertIsNone(journal['pending'])

    def test_real_collection_finishes_across_listener_restarts(self):
        self.exercise(False)

    def test_original_final_label_reproduces_stale_boot_refusal(self):
        self.exercise(True)

    def test_ram_preservation_keeps_original_game_transcript(self):
        original = h.T / 'build/hardware02'
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / 'serial.bin').write_bytes(b'original game transcript')
            bench = object.__new__(h.Bench)  # test-only physical I/O replacement
            bench.kit = json.loads((original / 'kit.json').read_text())
            bench.remote = bench.kit['remote']
            bench.cli = lambda where, label: (where / 'serial.bin').write_bytes(b'CLI proof')
            bench.get = lambda endpoint: dict(online=True)
            bench.upload = bench.exit = bench.line = bench.wait_online = Mock()
            bench.transfer = lambda where, label, operation, remote, local: shutil.copyfile(
                original / 'evidence/full-game/ram.bin', local)
            bench.save_guest_ram(folder)
            self.assertEqual((folder / 'serial.bin').read_bytes(), b'original game transcript')
            self.assertEqual((folder / 'preserve-cli-proof/serial.bin').read_bytes(), b'CLI proof')
            self.assertTrue(json.loads((folder / 'ram-preserved.json').read_text())['before_any_load_or_reset'])


if __name__ == '__main__':
    unittest.main()
