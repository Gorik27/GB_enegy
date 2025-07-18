from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np
from wizard.io import read_xyz, read_restart
from wizard.atoms import Morph

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("--ftol", required=False, default='1.0e-8', help='force tolerance for FIRE minimizer')
parser.add_argument("--maxiter", required=False, default='100000', help='max. number of iterations for FIRE minimizer')
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
args = parser.parse_args()

os.chdir('scripts')

outname = f'../workspace/{args.name}/dump/CNA/Epure.txt'

atoms = read_xyz(f'../workspace/{args.name}/dat/model.xyz')[0]

run_in = ['potential UNEP_v1.txt',
        f'minimize fire {args.ftol} {args.maxiter} 1',
        'velocity 0.000000000001',
        'ensemble nve',
        'time_step 0',
        'dump_restart 1',
        'dump_exyz 1', 
        'run 1']

tmp_path = f'../workspace/{args.name}/tmp/relax_box'
if os.path.exists(tmp_path):
    shutil.rmtree(tmp_path)
Morph(atoms).gpumd(tmp_path, run_in, nep_path='../potentials/UNEP_v1.txt')

run_in = ['potential UNEP_v1.txt',
        f'minimize fire {args.ftol} {args.maxiter}',
        'velocity 0.000000000001',
        'ensemble nve',
        'time_step 0',
        'dump_exyz 1', 
        'run 1']

print(run_in)

atoms = read_restart(f'{tmp_path}/restart.xyz')
tmp_path = f'../workspace/{args.name}/tmp/relax'
if os.path.exists(tmp_path):
    shutil.rmtree(tmp_path)
Morph(atoms).gpumd(tmp_path, run_in, nep_path='../potentials/UNEP_v1.txt')

shutil.copyfile(f'../workspace/{args.name}/tmp/relax/dump.xyz', f'../workspace/{args.name}/dat/relaxed.xyz')

#E = atoms.info['energy']
#print(E)
#np.savetxt(outname, np.array([E]))

print('All done')