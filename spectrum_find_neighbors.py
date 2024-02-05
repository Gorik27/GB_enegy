from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np
from ase import io
import pyscal as pc


parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("--treshold", required=False, type=float, default=0.02)

args = parser.parse_args()


file = f'workspace/{args.name}/dump/CNA/dump_0.cfg'
file_converted  = f'workspace/{args.name}/dump/CNA/dump_0.dat'
outname = f'workspace/{args.name}/dump/CNA/neigbors.txt'
outname_weights = f'workspace/{args.name}/dump/CNA/neigbors_weights.txt'
file_gb = f'workspace/{args.name}/dump/CNA/GBs.txt'
print(f'reading GB indicies in {file_gb}\n')
gb_ids = np.loadtxt(file_gb)[:, 0]
print(f'num. of GB atoms {len(gb_ids)}')

print(f'ase: reading file {file}...')
aseatoms = io.read(file)
print(' done\n')
sys = pc.System()
print(f'loading to pyscal...')
sys.read_inputfile(aseatoms, format='ase')
print(' done\n')
print('pyscal: building neighbor list using Voronoi method...')
sys.find_neighbors(method='voronoi')
print(' done\n')
print('converting to python format...')
atoms = sys.atoms
coord = [atom.coordination for atom in atoms]
neighbors = [atom.neighbors for atom in atoms]
neighbor_weights = [atom.neighbor_weights for atom in atoms]
ids = [atom.id for atom in atoms]
print(' done\n')
w_treshold = args.treshold
print(f'area treshold {w_treshold}; filtering...')

out = 'central atom. coordination. neighbor_ids\n'
out_weights = 'central atom. coordination. neighbor_weights\n'
ncount = 0
ncount2 = 0
zcount = 0
for i in range(len(neighbors)):
    if ids[i] in gb_ids:
        list_pre = neighbors[i]
        weights = neighbor_weights[i]
        norm = np.sum(weights)
        list_post = []
        weights_post = []
        for j in range(len(list_pre)):
            #filter only GB atoms through neighbors and neglecting too small facets of Voronoi polyhedra
            if (ids[list_pre[j]] in gb_ids) and (weights[j]/norm > w_treshold): 
                list_post.append(ids[list_pre[j]])
                weights_post.append(weights[j])
                # skip already icluded pairs
                #if not ids[list_pre[j]] in ids[:i]: # check if not neighbor already was an central atom
                #    list_post.append(ids[list_pre[j]])
                #    weights_post.append(weights[j])
        out += f'{ids[i]} {len(list_post)} '
        out_weights += f'{ids[i]} {len(list_post)} '
        ncount += len(list_post)

        for i in range(len(list_post)):
                out += f'{list_post[i]} '
                out_weights += f'{weights_post[i]} '
        out += '\n'
        out_weights += '\n'

print(f'saving neighbors to file: {outname}...')
with open(outname, 'w') as f:
    f.write(out)
print(f'saving weights to file: {outname_weights}...')
with open(outname_weights, 'w') as f:
    f.write(out_weights)
print(f'Total num. of neighbors {ncount}')
print('All done')