from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np
from wizard.io import read_xyz
from wizard.atoms import Morph

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("--id", required=True, type=int)
parser.add_argument("--ftol", required=False, default='1.0e-8', help='force tolerance for FIRE minimizer')
parser.add_argument("--maxiter", required=False, default='100000', help='max. number of iterations for FIRE minimizer')
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("-f", "--force", default=False, action='store_true', required=False,
                     help='force to restart calculations')
args = parser.parse_args()

os.chdir('scripts')

    
id_file = f'../workspace/{args.name}/dump/CNA/GBs.txt'
outname = f'../workspace/{args.name}/dump/CNA/bulkEs.txt'

selected = np.loadtxt(id_file).astype(int)
if len(selected.shape)==1:
    ids = selected
elif selected.shape[1]==2:
    ids = selected[:,0]
else:
    raise ValueError(f'Unexpected size of GBs.txt file (number of columns)! Expected to has 1 (id) or 2 (id cna) columns ')

if args.id in ids:
    raise ValueError(f'{args.id} is ID of GB atom!!!!')

id = args.id

atoms = read_xyz(f'../workspace/{args.name}/dat/relaxed.xyz')[0]

from datetime import datetime
now = datetime.now()
print('Starting time: ', now.strftime("%H:%M:%S"))

print(f'#id {id}')

cs = atoms.get_chemical_symbols()
cs[id] = 'Ni'
atoms.set_chemical_symbols(cs)

run_in = ['potential UNEP_v1.txt',
        f'minimize fire {args.ftol} {args.maxiter}',
        'velocity 0.000000000001',
        'dump_thermo 1',
        'ensemble nve',
        'time_step 0',
        'run 1']
tmp_path = f'../workspace/{args.name}/tmp/bulk_{id}'
if os.path.exists(tmp_path):
    shutil.rmtree(tmp_path)
Morph(atoms).gpumd(tmp_path, run_in, nep_path='../potentials/UNEP_v1.txt')

df = np.loadtxt(f'{tmp_path}/thermo.out')

E = df[2]
id0 = id

print(f'E {E}')
np.savetxt(outname, np.array([E]))
print('All done')