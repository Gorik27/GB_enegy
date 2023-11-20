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
parser.add_argument("--offset", required=False, type=int, default=0)
parser.add_argument("--id", required=False, type=int, default=-1)
parser.add_argument("-s", "--structure", required=False)
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("-p", "--plot", default=False, action='store_true', required=False, help='only plot graphics')
parser.add_argument("-m", "--mean-width", dest='mean_width', required=False, default=50, type=int)
parser.add_argument("--dump-step", dest='dump_step', required=False, type=int)
parser.add_argument("--np", required=False, default=1)
args = parser.parse_args()

os.chdir('scripts')

structure = args.structure
if not structure:
    fname = f'../workspace/{args.name}/conf.txt'
    flag=False
    with open(fname, 'r') as f :
        for line in f:
            if 'minimized' in line:
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
                #print(t)
                neighbors.append(np.array(t).astype(int))
                #print(neighbors[-1])
            else:
                i += 1

out = np.zeros((len(ids_central), np.max(zs)))
for i, id1 in enumerate(ids_central):
    print(f'#{i+1}/{len(ids_central)} id_central {id1}')
    for j, id2 in enumerate(neighbors[i]):
        print(f'    #{j+1}/{len(neighbors[i])} id {id2}')
        task = f'mpirun -np {args.np} lmp_intel_cpu_openmpi -in in.seg_int_minimize -var name {args.name} -var structure_name {structure} -var id1 {id1} -var id2 {id2} -sf omp -pk omp {args.jobs}'
        exitflag = False
        db_flag = False
        db = 0
        out[i, 0] = id1
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
        
        out[i, j+1] = E
    np.savetxt(outname, out, header='id [Es]')
print('All done')