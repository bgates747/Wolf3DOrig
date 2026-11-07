"""Source-equivalent WL_MAIN.C BuildTables data; no target runtime libm."""
from pathlib import Path
import math,struct,json,hashlib

def tables():
    radtoint = struct.unpack('<f',struct.pack('<f',1800 / 3.141592657))[0]
    values = [0]*900
    for i in range(450):
        tangent = math.tan((i+0.5)/radtoint)
        values[i] = int(tangent*65536)
        values[899-i] = int((1/tangent)*65536)
    assert all(0 < n < 0x80000000 for n in values)
    assert values == sorted(values)
    return values,radtoint

def write(path):
    values,radtoint=tables();p=Path(path)
    text='// Generated from pinned original WL_MAIN.C BuildTables formula.\n'
    text+='// Historical Borland libm byte identity is not claimed.\n'
    text+='static const int32_t kWolfFineTangent[900] __attribute__((aligned(4))) = {\n'
    text+=''.join('    '+', '.join(map(str,values[i:i+8]))+',\n' for i in range(0,900,8))+'};\n'
    with p.open('x') as f:f.write(text)
    return dict(entries=len(values),radtoint=radtoint,minimum=values[0],maximum=values[-1],sha256=hashlib.sha256(text.encode()).hexdigest())

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('output');print(json.dumps(write(p.parse_args().output)))
