from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np
from datetime import datetime

sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("-j", "--jobs", type=int, required=False, default=1)
parser.add_argument("-f", "--force", default=False, action='store_true', required=False,
                     help='force to restart calculations')
parser.add_argument("--id", required=False, type=int, default=-1)
parser.add_argument("-s", "--structure", required=False)
parser.add_argument("-o", "--old_suffix", required=False, default='')
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("--np", required=False, default=1)
parser.add_argument("--part", required=False, type=str, default='0_1',
                     help='to divide workflow on parts type: n_m (n<m) where m number of parts and n is a number of selected part (from 0 to m-1)')
args = parser.parse_args()

idpart, nparts = map(int, args.part.split('_'))
assert idpart<nparts
assert idpart>=0

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
if args.old_suffix:
    id_file_old = f'../workspace/{args.name}/dump/CNA/neigbors{args.old_suffix}.txt'
    outname_old = f'../workspace/{args.name}/dump/CNA/GBEs_int{args.old_suffix}.txt'
if args.part == '0_1':
    outname = f'../workspace/{args.name}/dump/CNA/GBEs_int.txt'
else:
    outname = f'../workspace/{args.name}/dump/CNA/GBEs_int_{args.part}.txt'
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
Z = np.sum(zs)
print(f'Total number of neighbors: {Z}')


neighbors_old = []
zs_old = []
if args.old_suffix:
    out_old = np.loadtxt(outname_old)
    with open(id_file_old, 'r') as f:
        i = 0
        for line in f:
            if '#' not in line:
                line = line.replace('\n', '')
                if i>0:
                    df = line.split(' ')
                    assert ids_central[i-1] == int(df[0])
                    zs_old.append(int(df[1]))
                    t = df[2:]
                    t.remove('')
                    neighbors_old.append(np.array(t).astype(int))
                    i += 1
                else:
                    i += 1
    Z_old = np.sum(zs_old)
    print(f'Total number of neighbors already calculated: {Z_old}')

volume = np.ceil(Z/nparts)
a = volume*idpart
if idpart == nparts-1:
    b = Z
else:
    b = a + volume
zsums = np.cumsum(zs)
ia = np.where(zsums>a)[0][0]
ib = np.where(zsums<=b)[0][-1]
ids_central = ids_central[ia:ib+1]
zs = zs[ia:ib+1]
neighbors = neighbors[ia:ib+1]

if args.old_suffix:
    zs_old = zs_old[ia:ib+1]
    neighbors_old = neighbors_old[ia:ib+1]  
    out_old = out_old[ia:ib+1]  
print('Selected part: ', ia, ib)
'''# tweak for restoring of work done without dividing in parts
out = np.loadtxt(f'../workspace/{args.name}/dump/CNA/GBEs_int.txt')
np.savetxt(outname, out[ia:ib+1], header='id [Es]')
exit()
'''

if (not args.force) and os.path.isfile(outname):
    out = np.loadtxt(outname)
    calculated_ids_c = out[:, 0]
    i0 = np.where(calculated_ids_c==0)[0][0]
    j0 = np.where(out[i0-1, 1:] == 0)[0][0]
    if j0 == zs[i0-1]:  # all neighbors of central atom (i0-1) was calculated 
        j0 = 0          # so we continue from i0, j0=0
    else:           # some neighbors of central atom (i0-1) was not calculated 
        i0 -= 1     # so we continue from (i0-1) j0
    print(f'found previous calculations, continue from #{i0}/{len(out)} central atom, #{j0}/{zs[i0]} neighbor')
else:
    i0 = 0
    j0 = 0
    print(f'starting new calculation')
    out = np.zeros((len(ids_central), 1+np.max(zs)))

if args.jobs == 1:
    suffix = ''
else:
    suffix = f' -sf omp -pk omp {args.jobs} '

now = datetime.now()
print('Starting time: ', now.strftime("%H:%M:%S"))
for i in range(i0, len(ids_central)):
    id1 = ids_central[i]
    print(f'#{i+1}/{len(ids_central)} id_central {id1}')
    out[i, 0] = id1
    for j in range(j0, len(neighbors[i])):
        id2 = neighbors[i][j]
        print(f'    #{j+1}/{len(neighbors[i])} id {id2}')
        if args.old_suffix:
            if id2 in neighbors_old[i]:
                j_old = np.where(neighbors_old[i]==id2)[0][0]+1
                print(f'    already calculated {id1}-{id2} j_old {j_old} E {out_old[i][j_old]}')
                out[i][j+1] = out_old[i][j_old]
                continue
        task = f'mpirun -np {args.np} {lmp} -in in.seg_int_minimize -var name {args.name} -var structure_name {structure} -var id1 {id1} -var id2 {id2} {suffix}'
        exitflag = False
        db_flag = False
        db = 0
        
        #print(task)
        with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
            time.sleep(0.1)
            print('\n')
            for line in p.stdout:
                if "Dangerous builds" in  line:
                    db = int(line.split()[-1])
                    if db>0:
                        db_flag = True
                elif "dumpfile" in line:
                    dumpfile = (line.replace('dumpfile ', '')).replace('\n', '')
                elif "datfile" in line:
                    datfile = (line.replace('datfile ', '')).replace('\n', '')
                elif "Seg energy" in line:
                    #print((line.replace('Seg energy ', '')).replace('\n', ''))
                    E = float((line.replace('Seg energy ', '')).replace('\n', ''))
                elif "All done" in line:
                    exitflag = True
                if not args.verbose:
                    if '!' in line:
                        print(line.replace('!', ''), end='')
                else:
                    print(line, end='')   
                        
        if not exitflag:
            raise ValueError('Error in LAMMPS')

        print('    done\n')
        if db > 0:
            print(f'WARNING!!!\nDengerous neighboor list buildings: {db}')

        print(f'    E {E}')
        
        out[i, j+1] = E
    np.savetxt(outname, out, header='id [Es]')
print('All done')