"""Finite serial ESP32 builds with owned-child thermal/RAM/time cleanup."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,time
HERE=Path(__file__).resolve().parent
ENV=Path('/Agon/mystuff/agon-dev-env')
PIO=Path('/Agon/mystuff/agon-vdplet/.venv/bin/pio')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def stop(proc):
    if proc.poll()is None:
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=5)


def build(revision,attempt,lease):
    base=HERE/'build'/revision
    inputs=json.loads((base/(attempt+'-inputs.json')).read_text())
    receipts={};began=time.monotonic()
    for backend,item in inputs.items():
        project=Path(item['project'])
        for relative,digest in item['files'].items():
            if sha(project/relative)!=digest:raise ValueError('native source drift: '+relative)
        subprocess.run([str(ENV/'.venv/bin/python'),str(ENV/'cross-agent/pi5-workloads/pi5_lease.py'),'assert-owner','--owner','wolf3dorig','--lease',lease],check=True,stdout=subprocess.DEVNULL)
        telemetry=[];proc=None;failure=None
        command=['nice','-n','10',str(PIO),'run','-d',str(project),'-e','esp32dev','-j','1']
        with (project/'build.log').open('x')as log:
            try:
                proc=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,env=dict(os.environ,PLATFORMIO_SETTING_ENABLE_TELEMETRY='No'))
                while proc.poll()is None:
                    temp=int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000
                    mem={line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')}['MemAvailable']
                    elapsed=time.monotonic()-began
                    telemetry.append({'elapsed':elapsed,'temperature_c':temp,'available_kib':mem})
                    if temp>=80 or mem<512*1024 or elapsed>900:raise RuntimeError('declared temperature/RAM/time bound reached')
                    time.sleep(1)
                if proc.returncode:raise RuntimeError('compiler exit '+str(proc.returncode))
                artifact=project/'.pio/build/esp32dev'
                receipts[backend]={'command':command,'returncode':proc.returncode,
                    'outputs':{name:{'bytes':(artifact/name).stat().st_size,'sha256':sha(artifact/name)}for name in ('firmware.bin','firmware.elf','firmware.map')},
                    'telemetry':telemetry}
            except Exception as error:
                failure=str(error);receipts[backend]={'command':command,'error':failure,'telemetry':telemetry}
            finally:
                if proc is not None:stop(proc)
                (base/(attempt+'-build.json')).write_text(json.dumps(receipts,indent=2)+'\n')
        print(backend+': '+(failure or 'build passed'),flush=True)
        if failure:
            print((project/'build.log').read_text()[-6000:],flush=True)
            raise RuntimeError(failure)
    print('Both task-owned firmware builds complete; no upload performed.',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--revision',required=True);p.add_argument('--attempt',required=True);p.add_argument('--lease',required=True)
    a=p.parse_args();build(a.revision,a.attempt,a.lease)
