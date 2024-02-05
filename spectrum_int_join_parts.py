from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np

sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("--parts", required=True, type=int,
                     help='join work splited on N parts')
args = parser.parse_args()
outname = f"workspace/{args.name}/dump/CNA/GBEs_int.txt"

print(args.parts)
lst = glob.glob(f"workspace/{args.name}/dump/CNA/GBEs_int*_{args.parts}.txt")
lst = sorted(lst, key=(lambda x: int((x.split('/')[-1]).split('_')[2])))

zs = []
for file in lst:
    out_i = np.loadtxt(file)
    zs.append(out_i.shape[1])
    print(file)

z = np.max(zs)

out_i = np.loadtxt(lst[0])
if out_i.shape[1]<z:
    t = np.zeros((out_i.shape[0], z))
    t[:, :out_i.shape[1]] = out_i
    out_i = t
np.savetxt(outname, out_i, header='id [Es]')
for file in lst[1:]:
    out_i = np.loadtxt(file)
    if out_i.shape[1]<z:
        t = np.zeros((out_i.shape[0], z))
        t[:, :out_i.shape[1]] = out_i
        out_i = t
    with open(outname, 'ab') as f:
        np.savetxt(f, out_i)

print('All done')