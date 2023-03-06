from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np
sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp


def main(args):
    structure = args.structure

    task = f'{lmp} -in in.berendsen_relax_init -var name {args.name} -var structure_name {structure} -sf omp -pk omp {args.jobs}'
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


    new_datfile = f"{datfile.replace('.dat', '')}_{args.postfix}.dat"
    os.rename(f'../workspace/{args.name}/dat/{datfile}',
              f'../workspace/{args.name}/dat/{new_datfile}')
    output = f'heated {new_datfile}\n'
    with open(f'../workspace/{args.name}/conf.txt', 'a+') as f:
        f.write(output)
    print(f'wrote to conf.txt:\n>{output}')
    
    print('plotting...')
    impath = f'../workspace/{args.name}/images'
    Path(impath).mkdir(exist_ok=True)  
    outpath = f'../workspace/{args.name}/thermo_output'
    Path(outpath).mkdir(exist_ok=True)  
    from scripts.plot_thermal_relax import main as plot
    parser = argparse.ArgumentParser()
    plot_args = parser.parse_args()
    plot_args.name = args.name
    plot_args.postfix = args.postfix
    plot_args.n = args.mean_width
    plot_args.inp = thermo.replace('.txt', '')
    plot(plot_args)

    print('\n\nstep #2 done')
    return new_datfile


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", required=True)
    arser.add_argument("--postfix", required=False, default='', help="add this postfix at the end of output file's names")
    parser.add_argument("-j", "--jobs", type=int, required=False, default=1)
    parser.add_argument("--offset", required=False, type=int, default=0)
    parser.add_argument("-s", "--structure", required=False)
    parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
    parser.add_argument("-m", "--mean-width", dest='mean_width', required=False, default=50, type=int)
    parser.add_argument("--min-grain", dest='min_grain', required=False, default=1000, type=int)
    parser.add_argument("--dump-step", dest='dump_step', required=False, type=int)
    parser.add_argument("--save", default=False, action='store_true', required=False,
                        help='save plotting data in file') 
    args = parser.parse_args()
    main(args)
