from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np
from wizard.io import read_xyz
from wizard.atoms import Morph

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("-o", "--idfile", default='GBs.txt', 
                    help='filename in <project/dump/CNA> folder with inds of GB sites to compute')
parser.add_argument("-s", "--structure", default='relaxed.xyz')
parser.add_argument("--ftol", required=False, default='1.0e-8', help='force tolerance for FIRE minimizer')
parser.add_argument("--maxiter", required=False, default='100000', help='max. number of iterations for FIRE minimizer')
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("-f", "--force", default=False, action='store_true', required=False,
                     help='force to restart calculations')
args = parser.parse_args()

os.chdir('scripts')

    
id_file = f'../workspace/{args.name}/dump/CNA/{args.idfile}'
outname = f'../workspace/{args.name}/dump/CNA/GBEs.txt'

selected = np.loadtxt(id_file).astype(int)
if len(selected.shape)==1:
    ids = selected
elif selected.shape[1]==2:
    ids = selected[:,0]
else:
    raise ValueError(f'Unexpected size of GBs.txt file (number of columns)! Expected to has 1 (id) or 2 (id cna) columns ')
i0 = 0

if (not args.force) and os.path.isfile(outname):
    out = np.loadtxt(outname)
    calculated_ids = out[:, 0]
    i0 = np.where(calculated_ids==0)[0][0]
    print(f'found previous calculations, continue from #{i0}/{len(out)} point')
else:
    print(f'starting new calculation')
    out = np.zeros((ids.shape[0], 2))

atoms = read_xyz(f'../workspace/{args.name}/dat/{args.structure}')[0]
id0 = -1

from datetime import datetime
now = datetime.now()
print('Starting time: ', now.strftime("%H:%M:%S"))

for i in range(i0, len(ids)):
    id = ids[i]
    print(f'#{i+1}/{len(ids)} id {id}')
    
    cs = atoms.get_chemical_symbols()
    if id0 != -1:
        cs[id0] = 'Ag'
    cs[id] = 'Ni'
    atoms.set_chemical_symbols(cs)

    run_in = ['potential UNEP_v1.txt',
            f'minimize fire {args.ftol} {args.maxiter}',
            'velocity 0.000000000001',
            'ensemble nve',
            'time_step 0',
            'dump_xyz -1 relaxed.xyz',
            'dump_thermo -1',
            'run 1']
    tmp_path = f'../workspace/{args.name}/tmp/spectrum_{id}'
    if os.path.exists(tmp_path):
        shutil.rmtree(tmp_path)
    Morph(atoms).gpumd(tmp_path, run_in, nep_path='../potentials/UNEP_v1.txt')

    df = np.loadtxt(f'{tmp_path}/thermo.out')

    E = df[2]
    id0 = id

    print(f'E {E}')
    out[i, 0] = id
    out[i, 1] = E
    np.savetxt(outname, out, header='id E')
print('All done')