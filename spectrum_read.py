from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np
from ase import io

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)

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
