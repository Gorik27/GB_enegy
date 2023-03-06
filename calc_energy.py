from pathlib import Path
import argparse, os, sys, shutil

from subprocess import Popen, PIPE
from copy import deepcopy
import time, re, shutil, sys, glob
import numpy as np
sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp
from scripts.create import main as _create 
from scripts.berendsen_init import main as _berendsen_init
from scripts.segregation import main as _segregation
from matplotlib import pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("-j", "--jobs", type=int, required=False, default=1)
parser.add_argument("--offset", required=False, type=int, default=0)
parser.add_argument("-Ns", required=True, nargs='+', type=int, help='list of number of grains')
parser.add_argument("-c", "--conc", required=False, default=-1, type=float)
parser.add_argument("--iterations", required=False, default=1, type=int, help='number of iterations for averaging energy over samples of polytcrystalls')
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("-f", "--force", default=False, action='store_true', required=False, help='overwrite all steps')
parser.add_argument("-m", "--mean-width", dest='mean_width', required=False, default=50, type=int)
parser.add_argument("--loops", required=False, default=100, type=int,
                    help='during segregation draw the thermodynamic plot each <N> loops')
args = parser.parse_args()

os.chdir('scripts')

fname = f'../workspace/{args.name}/conf.txt'
flag = os.path.isfile(fname) 
Es = []
Ns = args.Ns
'''
conf.txt
step 1
sample 1
created structure_created #index=1
heated structure_heated #index=2
energy E_value #index=3
sample 2
created structure_created #index=1
heated structure_heated #index=2
energy E_value #index=3
step 2
sample 1
created structure_created #index=1
heated structure_heated #index=2
energy E_value #index=3
sample 2
created structure_created #index=1
heated structure_heated #index=2
energy E_value #index=3

'''
index = 0
step0 = 0
sample0 = 0
step_flag = False
sample_flag = False
if args.force:
    flag = False

if not flag:
    with open(fname, 'w') as f :
        f.write('')
else:
    with open(fname, 'r') as f :
        lines = list(f)
        if ('step' in lines[-1]) or ('step' in lines[-2]):
            step_flag = True
        if ('sample' in lines[-1]) or ('sample' in lines[-2]):
            sample_flag = True
        for line in lines:
            if 'step ' in line:
                s = int(line.split(' ')[-1])
                if step0 < s:
                    print()
                    index = 0
                    sample0 = 0
                    step0 = s
            if 'sample ' in line:
                s = int(line.split(' ')[-1])
                if sample0 < s:
                    index = 0
                    sample0 = s
            if 'created ' in line:
                index = max(index, 1)
                structure_created = line.split(' ')[-1]
            if 'heated ' in line:
                index = max(index, 2)
                structure_heated = line.split(' ')[-1]
            if 'energy ' in line:
                index = max(index, 3)
                E_value = float(line.split(' ')[-1])
                Es.append(E_value)
            

def create(*fargs):
    N = fargs[0]
    L = fargs[1]
    _args = deepcopy(args)
    _args.N = N
    _args.L = L
    _args.postfix = fargs[2]
    global structure_created
    structure_created = _create(_args)

def berendsen_init(*fargs):
    _args = deepcopy(args)
    _args.min_grain = 1000
    _args.dump_step = None
    _args.save = False
    _args.structure = structure_created
    _args.postfix = fargs[2]
    global structure_heated
    structure_heated = _berendsen_init(_args)

def segregation(*fargs):
    _args = deepcopy(args)
    _args.min_grain = 1000
    _args.dump_step = None
    _args.save = False
    _args.structure = structure_heated
    global E
    _args.mu = None
    _args.kappa = -1
    _args.plot = False
    _args.postfix = fargs[2]
    E = _segregation(_args)

actions = [create, berendsen_init, segregation]
Lx, Ly, Lz = 100, 100, 100

if index == 3:
    if sample0 == args.iterations-1:
        sample0 = 0
        step0 += 1
        index = 0
    else:
        sample0 += 1
        index = 0

print(f'starting from {step0} step, {sample0} sample, {index}/3')
for step in range(step0, len(Ns)):
    if (index == 0) and (not step_flag):
        with open(fname, 'a') as f :
                    f.write(f'step {step}\n')
    for sample in range(sample0, args.iterations):
        if (index == 0) and (not sample_flag):
            with open(fname, 'a') as f :
                    f.write(f'sample {sample}\n')
        for i in range(index, 3):
            fargs = (Ns[step], [Lx, Ly, Lz], f'step_{step}_smpl_{sample}')
            actions[i](*fargs)
        Es.append(E)

E_mean = []
E_sum = 0
for i in range(len(Es)):
    E_sum += Es[i]
    if i%args.iterations == args.iterations-1:
        E_mean.append(E_sum/args.iterations)
        E_sum = 0

plt.plot(Ns, E_mean-np.min(E_mean), 'o')
plt.xlabel('$N$')
plt.ylabel('$E, eV/atom$')
plt.savefig(f'../workspace/{args.name}/images/Energy_vs_Ngrains.png')