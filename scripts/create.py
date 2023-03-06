from pathlib import Path
import argparse, os, sys, shutil
from subprocess import Popen, PIPE
import time, re, shutil, sys, glob
import numpy as np
sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp

def main(args):
    outname = 'polycrystall'
    task = f'{lmp} -in in.find_minimum -var name {args.name} -sf omp -pk omp {args.jobs}'
    exitflag = False

    print('finding structure...')
    print(task)
    with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
        time.sleep(0.1)
        print('\n')
        for line in p.stdout:
            if "lattice found" in  line:
                exitflag = True
            if '!!' in line:
                s = line.replace('!!', '')
                s = s.replace('%', "'")
                if 'lat' in s:
                    lat = (s.split(' ')[-1]).replace("'", '').replace("\n", '')
                if 'a0' in s:
                    a0 = float(s.split(' ')[-1])
                if 'element1' in s:
                    element1 = (s.split(' ')[-1]).replace("'", '').replace("\n", '')
                if 'ecoh' in s:
                    ecoh = float(s.split(' ')[-1])
                print(s, end='')
            elif (not args.verbose) and ('!' in line):
                print(line.replace('!', ''), end='')
            elif args.verbose:
                print(line, end='')   
                    
    if not exitflag:
        raise ValueError('Error in LAMMPS')

    atmsk_path = f'../workspace/{args.name}/tmp_atomsk'
    Path(atmsk_path).mkdir(exist_ok=True)
    os.chdir(atmsk_path)

    print('done\ncreating lattice seed...')

    task = f'atomsk --create {lat} {a0} {element1} lammps -overwrite'
    print(task)
    with Popen(task.split(), stdout=PIPE, stdin=PIPE, bufsize=1, universal_newlines=True) as p:
        for line in p.stdout:
            if args.verbose:
                print(line, end='')  
            elif 'ERROR' in line:
                print(line)

    Path(f'../dat').mkdir(exist_ok=True) 
    shutil.move(f'{element1}.lmp', f'../dat/{element1}.dat')
    print('done\n')
    print('All done')

    print('done\ncreating polycrystal...')
    N = args.N
    Lx, Ly, Lz = args.L

    fname = 'polycrystal.txt'
    file = f"""
    box {Lx} {Ly} {Lz}
    random {N}
    """
    with open(fname, 'w') as f:
        f.write(file)

    exitflag = False

    task = f'atomsk --polycrystal ../dat/{element1}.dat {fname} {outname}.lmp -wrap -overwrite -nthreads {args.jobs}'
    print(task)
    with Popen(task.split(), stdout=PIPE, stdin=PIPE, bufsize=1, universal_newlines=True) as p:
        for line in p.stdout:
            if args.verbose:
                print(line, end='')  
            elif 'ERROR' in line:
                print(line)
            '''
            if 'Do you want to overwrite it (y/n)' in line:
                p.stdin.write("y\n")
            if 'Y=overwrite all' in line:
                p.stdin.write("Y\n")
            '''
    shutil.move(f'{outname}.lmp', f'../dat/{outname}.dat')
    print('done\n')

    os.chdir('../../../scripts')
    task = f'{lmp} -in in.minimize -var name {args.name} -var structure_name {outname}.dat -sf omp -pk omp {args.jobs}'
    exitflag = False

    print('relaxing structure...')
    print(task)
    with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
        time.sleep(0.1)
        print('\n')
        for line in p.stdout:
            if "All done" in  line:
                exitflag = True
            if "datfile" in  line:
                datfile = (line.replace('datfile ', '')).replace('\n', '')
            if '!!' in line:
                s = line.replace('!!', '')
                s = s.replace('%', "'")
                exec(s)
                print(s, end='')
            elif (not args.verbose) and ('!' in line):
                print(line.replace('!', ''), end='')
            elif args.verbose:
                print(line, end='')   
                    
    if not exitflag:
        raise ValueError('Error in LAMMPS')

    new_datfile = f"{datfile.replace('.dat', '')}_{args.postfix}.dat"
    os.rename(f'../workspace/{args.name}/dat/{datfile}',
              f'../workspace/{args.name}/dat/{new_datfile}')
    output = f'created {new_datfile}\n'
    conf_path = f'../workspace/{args.name}/conf.txt'
    with open(conf_path, 'a+') as f:
        f.write(output)

    print(f'wrote to conf.txt:\n>{output}\n\nstep #1 done')
    return new_datfile
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", required=True)
    arser.add_argument("--postfix", required=False, default='', help="add this postfix at the end of output file's names")
    parser.add_argument("-j", "--jobs", type=int, required=False, default=1)
    parser.add_argument("-v", "--verbose", default=False, action='store_true', required=False)
    parser.add_argument("-N", type=int, required=True, help='number of grains')
    parser.add_argument("-L", type=float, nargs=3, required=True, help='cell size in number in lattice constant (Lx Ly Lz)')
    args = parser.parse_args()
    main(args)
