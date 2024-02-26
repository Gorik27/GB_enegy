from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np

sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("-j", "--jobs", type=int, required=False, default=1)
parser.add_argument("-i", "--id", nargs='+', required=True)
parser.add_argument("-s", "--structure", required=False)
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("-f", "--force", default=False, action='store_true', required=False,
                     help='force to restart calculations')
parser.add_argument("-b", "--boxrelax", default=False, action='store_true', required=False,
                     help='fix box/relax turn on')
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

if args.boxrelax:
    boxrelax_arg = '_boxrelax'
else:
    boxrelax_arg = ''

ids_i_arg = (' '.join(str(id) for id in args.id))
ids_i_name = ('_'.join(str(id) for id in args.id))

id_file = f'../workspace/{args.name}/dump/CNA/GBs.txt'
outname = f'../workspace/{args.name}/dump/CNA/GBEs_id_{ids_i_name}{boxrelax_arg}.txt'

selected = np.loadtxt(id_file).astype(int)
ids = selected[:,0]
i0 = 0

if (not args.force) and os.path.isfile(outname):
    out = np.loadtxt(outname)
    calculated_ids = out[:, 0]
    i0 = np.where(calculated_ids==0)[0][0]
    print(f'found previous calculations, continue from #{i0}/{len(out)} point')
else:
    print(f'starting new calculation')
    out = np.zeros((ids.shape[0], 2))

if args.jobs == 1:
    suffix = ''
else:
    suffix = f' -sf omp -pk omp {args.jobs} '

from datetime import datetime
now = datetime.now()
print('Starting time: ', now.strftime("%H:%M:%S"))

for i in range(i0, len(ids)):
    id = ids[i]
    print(f'#{i+1}/{len(ids)} id {id} cna {selected[i, 1]}')
    task = f'mpirun -np {args.np} {lmp} -in in.seg_minimize_id{boxrelax_arg} -var name {args.name} -var structure_name {structure} -var id0 {ids_i_arg} -var id {id}  {suffix}'
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
                print((line.replace('Seg energy ', '')).replace('\n', ''))
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

    print('done\n')
    if db > 0:
        print(f'WARNING!!!\nDengerous neighboor list buildings: {db}')

    print(f'E {E}')
    out[i, 0] = id
    out[i, 1] = E
    np.savetxt(outname, out, header='id E')
print('All done')