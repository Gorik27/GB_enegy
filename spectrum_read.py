from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np
from ase import io

sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("-j", "--jobs", type=int, required=False, default=1)
parser.add_argument("--offset", required=False, type=int, default=0)
parser.add_argument("--id", required=False, type=int, default=-1)
parser.add_argument("-s", "--structure", required=False)
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("-p", "--plot", default=False, action='store_true', required=False, help='only plot graphics')
parser.add_argument("-m", "--mean-width", dest='mean_width', required=False, default=50, type=int)
parser.add_argument("--dump-step", dest='dump_step', required=False, type=int)
parser.add_argument("--np", required=False, default=1)
args = parser.parse_args()


file = f'workspace/{args.name}/dump/CNA/dump_0.cfg'
outname = f'workspace/{args.name}/dump/CNA/GBs.txt'

atoms = io.read(file)
cna = np.array(atoms.arrays['c_cna'])
id = np.array(atoms.arrays['id'])
selected = id[cna!=1]
print(f'find {len(selected)} GB atoms')
data = np.empty((len(selected), 2))
data[:,0] = selected
data[:,1] = cna[cna!=1]
print(f'saving to file: {outname}...')
np.savetxt(outname, data, fmt='%d', header='id cna')
print('All done')
