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
parser.add_argument("--np", required=False, default=1)          
parser.add_argument("--offset", required=False, type=int, default=0)
parser.add_argument("-s", "--structure", required=False)
parser.add_argument("--save", default=False, action='store_true', required=False,
    help='save plot data in file')
parser.add_argument("--postfix", required=False, default='', help="add this postfix at the end of output file's names")
parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
parser.add_argument("-p", "--plot", default=False, action='store_true', required=False, help='only plot graphics')
parser.add_argument("-m", "--mean-width", dest='mean_width', required=False, default=50, type=int)
parser.add_argument("--dump-step", dest='dump_step', required=False, type=int)
parser.add_argument("--thermo", required=False, default='berendsen_relax')
args = parser.parse_args()

os.chdir('scripts')
if not args.plot:
    structure = args.structure
    if not structure:
        fname = f'../workspace/{args.name}/conf.txt'
        flag=False
        with open(fname, 'r') as f :
            for line in f:
                if 'annealed' in line:
                    structure = line.split()[-1]
                    print(structure)
                    flag = True
        if not flag:
            raise ValueError(f'cannot find structure in conf.txt')

    script = 'in.berendsen_relax_cooling'

    if args.jobs == 1:
        suffix = ''
    else:
        suffix = f' -sf omp -pk omp {args.jobs} '
    task = f'mpirun -np {args.np} lmp_intel_cpu_openmpi -in {script} -var name {args.name} -var structure_name {structure} {suffix}'
    exitflag = False
    db_flag = False
    db = 0
    error_msg = ''

    print('starting LAMMPS...')
    print(task)
    with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
        time.sleep(0.1)
        print('\n')
        for line in p.stdout:
            if "Dangerous builds" in  line:
                db = int(line.split()[-1])
                if db!=0:
                    print('Dengerous builds:', db)
                    db_flag = True
            elif "dumpfile" in line:
                dumpfile = (line.replace('dumpfile ', '')).replace('\n', '')
            elif "datfile" in line:
                datfile = (line.replace('datfile ', '')).replace('\n', '')
            elif "thermo output" in line:
                thermo = (line.replace('thermo output ', '')).replace('\n', '')
            elif "All done" in line:
                exitflag = True
            elif "ERROR" in line:
                print(line)
                error_msg = line.replace('ERROR: ', '')
            
            if not args.verbose:
                if '!' in line:
                    print(line.replace('!', ''), end='')
            else:
                print(line, end='')   
                    
    if not exitflag:
        raise ValueError(f'Error in LAMMPS: {error_msg}')

    print('done\n')
    if db_flag:
        print(f'WARNING!!!\nDengerous neighboor list buildings: {db}')

    output=''
    flag = False
    with open(f'../workspace/{args.name}/conf.txt', 'r') as f :
        for line in f:
            if 'cooled' in line:
                line = f'cooled {datfile}\n'
                flag=True
                print(line)
                output += line
        if not flag:
            output += f'cooled {datfile}\n'

        with open(f'../workspace/{args.name}/conf.txt', 'w') as f:
            f.write(output)

print('plotting...')
impath = f'../workspace/{args.name}/images'
Path(impath).mkdir(exist_ok=True)  
outpath = f'../workspace/{args.name}/thermo_output'
Path(outpath).mkdir(exist_ok=True)  
from plot_thermal_relax import main as plot
plot_args = parser.parse_args()
plot_args.name = args.name
plot_args.n = args.mean_width
args.postfix = 'cooling'
if args.thermo:
    thermo = args.thermo
plot_args.inp = thermo.replace('.txt', '')
plot(plot_args)

print('All done')