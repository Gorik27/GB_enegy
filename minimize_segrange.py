from pathlib import Path
import argparse, os
from subprocess import Popen, PIPE
import time, re, sys
from glob import glob
import numpy as np
sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp
import logging
from collections.abc import Iterable
from datetime import datetime
from copy import deepcopy as dc

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True)
parser.add_argument("-j", "--jobs", type=int, required=False, default=1)
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("--np", required=False, default=1)
parser.add_argument("-k", "--kappa", required=False, default='*')
args = parser.parse_args()

def log(*msg):
    print(*msg)
    if isinstance(msg, Iterable):
        time = datetime.now().strftime("%H:%M")
        logging.info(f'[{time}]     '+' '.join(map(str, msg)))
    else:
        logging.info(f'[{time}]     '+str(msg))

logname = f'minimize_segrange_k_{args.kappa}'
logging.basicConfig(filename=f'workspace/{args.name}/{logname}.log', 
                    encoding='utf-8', 
                    format='%(message)s',
                    level=logging.INFO)

now = datetime.now()
current_time = now.strftime("%Y-%m-%d %H:%M:%S")
log(f'Current time: {current_time}')

os.chdir('scripts')

outfile = f'../workspace/{args.name}/out_minimize_segrange_k_{args.kappa}.txt'
structures = [s.split('/')[-1] for s in glob(f'../workspace/{args.name}/dat/segregation_cooling_*_k_{args.kappa}.dat')]
if len(structures)==0 and float(args.kappa)%1==0:
    structures = [s.split('/')[-1] for s in glob(f'../workspace/{args.name}/dat/segregation_cooling_*_k_{int(float(args.kappa))}.dat')]
if len(structures)==0:
    raise ValueError(f'There is no files "segregation_cooling_*_k_{args.kappa}.dat"')
    
structure0 = [s.split('/')[-1] for s in glob(f'../workspace/{args.name}/dat/cooled_*.dat')]

if len(structure0)>1:
    log(f"""More than one file in structure0 (before segregation): {structure0}
Only the firs would be selected!""")

structure0 = structure0[0]
log(f"""...
Found structures:     
{structures}
Structure before segregation:
{structure0}
""")
structures_all = dc(structures)
structures_all.insert(0, structure0)

for i, structure in enumerate(structures_all):
    if i==0:
        routine = 'in.minimize_segrange0'
    else:
        routine = 'in.minimize_segrange'
    task = f'mpirun -np {args.np} {lmp} -in {routine} -var name {args.name} -var structure_name {structure} -sf omp -pk omp {args.jobs}'
    exitflag = False
    db_flag = False
    db = 0
    log(f"""starting LAMMPS...
{task}""")
    with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
        time.sleep(0.1)
        print('\n')
        for line in p.stdout:
            if "Dangerous builds" in  line:
                db = int(line.split()[-1])
                if db>0:
                    db_flag = True
                    db_print = db
            #print "Energy = $(v_Peng/atoms)"
            elif "Energy = " in line:
                energy = float(line.replace('Energy = ', '').replace('\n', ''))
            elif "All done" in line:
                exitflag = True
            if not args.verbose:
                if '!' in line:
                    log(line.replace('!', '').replace('\n', ''))
            else:
                log(line.replace('\n', ''))   
                
                    
    if not exitflag:
        raise ValueError(f'Error in LAMMPS, see "workspace/{args.name}/logs/{routine.replace("in.", "")}.log"')
    with open(outfile, 'a') as f:
        f.write(f'{structure} {energy}\n')
    log('done\n')
    if db_flag:
        log(f'WARNING!!!\nDengerous neighboor list buildings: {db_print}')

log(f"""All done!
Output in: {outfile.replace('../', '')}""")