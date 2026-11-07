"""Real producer selection and actual returned-error preservation regressions."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import json,tempfile,unittest
import hardware,guest_binding
T=Path(__file__).resolve().parent

class ProducerTests(unittest.TestCase):
    def bindings(self):return json.loads((T/'build/guests01/bindings.json').read_text())
    def test_actual_linked_producer_control_reproduction_and_stopped65_refusal(self):
        self.assertTrue(guest_binding.qualify(self.bindings())['passed'])
    def test_selected_module_dispatches_its_actual_guest_for_both_modes(self):
        for arm in ('original','candidate'):
            for mode in ('control','unpaced'):
                with self.subTest(arm=arm,mode=mode),tempfile.TemporaryDirectory() as folder:
                    b=object.__new__(hardware.Bench);g=self.bindings()
                    b.kit={'guests':g,**{a+'_module_sha256':g[a][mode]['module_sha256'] for a in g}}
                    b.selected_module_sha256=g[arm][mode]['module_sha256']
                    with patch.object(hardware.h.Bench,'invoke',return_value='actual-parent') as invoke:
                        self.assertEqual(b.invoke(Path(folder),'b-'+mode+'.bin','marker',mode=='control'),'actual-parent')
                        self.assertEqual(invoke.call_args.args[1],g[arm][mode]['remote_name'])
                    self.assertEqual(json.loads((Path(folder)/'guest-binding.json').read_text())['arm'],arm)
    def test_unknown_module_cannot_dispatch_a_guest(self):
        b=object.__new__(hardware.Bench);b.kit={'original_module_sha256':'old','candidate_module_sha256':'new'};b.selected_module_sha256='foreign'
        with patch.object(hardware.h.Bench,'invoke') as invoke:
            with self.assertRaisesRegex(AssertionError,'Unbound module'):b.invoke(None,'b-control.bin','marker',True)
            invoke.assert_not_called()
    def test_actual_terminal_prompt_recognition_requires_prompt_after_error(self):
        for after in (False,True):
            with self.subTest(after=after),tempfile.TemporaryDirectory() as folder:
                b=object.__new__(hardware.Bench);b.remote='/test/wolf/perf006/r01'
                prompt=b.remote.encode()+b' *';error=b'VDPlet startup/render failure: stage=07 status=03 value=000A callback=00'
                raw=bytearray(prompt+b'\r\n'+error+(b'\r\n'+prompt if after else b''))
                serial=SimpleNamespace(read=lambda _:b'')
                if after:
                    with self.assertRaises(hardware.h.SetupFailure):b.capture(serial,raw,Path(folder),lambda _:True,1)
                else:b.capture(serial,raw,Path(folder),lambda _:True,1)

class Preservation(hardware.Bench):
    def __init__(self,root,diagnostics):
        self.out=Path(root);self.remote='/test/wolf/perf006/r01';self.events=[];self.diagnostics=diagnostics
        guest=self.out/'guest.bin';guest.write_bytes(b'GUEST-RAM');self.kit={'stage':{'b-original-control.bin':str(guest)},'restore':'exact-restore'}
    def cli(self,*args):self.events.append('actual-cli')
    def service(self,*args):pass
    def raw_state(self,*args):pass
    def upload(self,p,label,local,remote):self.events.append('save-script')
    def exit(self,*args):pass
    def line(self,p,label,command):
        assert command.startswith('EXEC ');self.events.append('SAVE-before-LOAD')
    def wait_online(self,*args):pass
    def transfer(self,p,label,op,remote,local):
        assert op=='get';self.events.append(label)
        Path(local).write_bytes(b'GUEST-RAM' if label=='ram' else b'corrupt-preserved-diagnostic')
    def metadata(self,*args):return SimpleNamespace(entries=lambda _:[(self.remote+'/'+n,1,0) for n in self.diagnostics],lock=SimpleNamespace(close=lambda:None))
    def flash(self,label,image):assert label=='restore' and image=='exact-restore';self.events.append('exact-restore')
    def handback(self):self.events.append('handback')

class PreservationTests(unittest.TestCase):
    def test_missing_or_corrupt_optional_diagnostics_do_not_block_restore_after_ram(self):
        for names in ([],['loading.bin'],['loading.bin','loading3.bin']):
            with self.subTest(names=names),tempfile.TemporaryDirectory() as folder:
                b=Preservation(folder,names);b.preserve_setup()
                self.assertLess(b.events.index('ram'),b.events.index('exact-restore'))
                self.assertEqual(b.events[-2:],['exact-restore','handback'])
                p=Path(folder)/'failure-collection'
                self.assertTrue(json.loads((p/'ram-preserved.json').read_text())['before_any_load'])
                for n in ('loading.bin','loading3.bin'):
                    self.assertTrue((p/(n+('.decode-error.json' if n in names else '.absent.json'))).exists())

if __name__=='__main__':unittest.main()
