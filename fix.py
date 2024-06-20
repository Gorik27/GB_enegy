from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("-j", "--jobs", type=int, required=False, default=1)
parser.add_argument("--id", required=False, type=int, default=-1)
parser.add_argument("-s", "--structure", required=False)
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("-o", "--old", required=False, help='name of neighbor files with duplicated pairs if needed to fix')
parser.add_argument("--np", required=False, default=1)
args = parser.parse_args()

os.chdir('scripts')

structure = args.structure
if not structure:
    fname = f'../workspace/{args.name}/conf.txt'
    flag=False
    with open(fname, 'r') as f :
        for line in f:
            if 'ann_minimized' in line:
                structure = line.split()[-1]
                print(structure)
                flag = True
    if not flag:
        raise ValueError(f'cannot find structure in conf.txt')
    
id_file = f'../workspace/{args.name}/dump/CNA/neigbors.txt'
outname = f'../workspace/{args.name}/dump/CNA/GBEs_int.txt'
ids_central = []
neighbors = []
zs = []
with open(id_file, 'r') as f:
    i = 0
    for line in f:
        if '#' not in line:
            line = line.replace('\n', '')
            if i>0:
                df = line.split(' ')
                ids_central.append(int(df[0]))
                zs.append(int(df[1]))
                t = df[2:]
                t.remove('')
                neighbors.append(np.array(t).astype(int))
            else:
                i += 1

if args.old:
    ids_central_o = []
    neighbors_o = []
    zs_o = []
    id_file_o = f'../workspace/{args.name}/dump/CNA/{args.old}'
    with open(id_file_o, 'r') as f:
        i = 0
        for line in f:
            if '#' not in line:
                line = line.replace('\n', '')
                if i>0:
                    df = line.split(' ')
                    ids_central_o.append(int(df[0]))
                    zs_o.append(int(df[1]))
                    t = df[2:]
                    t.remove('')
                    neighbors_o.append(np.array(t).astype(int))
                else:
                    i += 1

if os.path.isfile(outname):
    out = np.loadtxt(outname)
    flag = True
    while flag:
        doflag = False
        calculated_ids_c = out[:, 0]
        i0 = np.where(calculated_ids_c==0)[0][0]
        if (zs[i0]==0) and (out[i0+1, 0]!=0):
            out[i0, 0] = ids_central[i0]
            print(f'add row {i0} for id {ids_central[i0]}')
            doflag = True
        elif (zs[i0]==0) and (zs[i0+1]==0) and (out[i0+2, 0]!=0):
            out[i0, 0] = ids_central[i0]
            print(f'add row {i0} for id {ids_central[i0]}')
            doflag = True
        else:
            j0 = np.where(out[i0-1, 1:] == 0)[0][0]
            if j0 == zs[i0-1]:  # all neighbors of central atom (i0-1) was calculated 
                j0 = 0          # so we continue from i0, j0=0
            else:           # some neighbors of central atom (i0-1) was not calculated 
                i0 -= 1     # so we continue from (i0-1) j0
            print(f'found previous calculations, continue from #{i0}/{len(out)} central atom, #{j0}/{zs[i0]} neighbor')
            if doflag:
                np.savetxt(outname, out, header='id [Es]')
            flag = False
    if args.old:
        cnt = 0
        out_f = np.zeros((len(ids_central), 1+np.max(zs)))
        for i in range(i0):
            assert ids_central[i] == ids_central_o[i]
            out_f[i, 0] = ids_central[i]
            if zs[i] < zs_o[i]:
                k = 0
                for j in range(zs_o[i]):
                    if j-k == zs[i]:
                        cnt += 1
                        break
                    if neighbors_o[i][j] != neighbors[i][j-k]:
                        cnt += 1
                        k += 1
                    else:
                        #print(out_f[i])
                        #print(out[i])
                        out_f[i, 1+j-k] = out[i, 1+j]
            else:
                out_f[i, 1:] = out[i, 1:out_f.shape[1]]
        np.savetxt(outname, out_f, header='id [Es]')
        print(cnt)
else:
    print(f'ERROR!!!!!!!!\nThere is no file {outname}!')

