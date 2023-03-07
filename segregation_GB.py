from pathlib import Path
import argparse, os
from subprocess import Popen, PIPE
import time, re, shutil, sys
import numpy as np
sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp
from plot_segregation import main as plot

def main(args):
    nonverbose = (not args.verbose)
    job = args.job
    name = args.name
    structure = args.structure
    N_loops = args.loops
    
    if not structure:
        fname = f'workspace/{name}/conf.txt'
        flag=False
        with open(fname, 'r') as f :
            for line in f:
                if 'relaxed' in line:
                    structure = line.split()[-1]
                    print(structure)
                    flag = True
        if not flag:
            raise ValueError(f'cannot find structure in conf.txt')
    if args.mu:
        mu_arg = f'-var mu0 {args.mu} '
    else:
        mu_arg = ''

    print(name, '\n')

    print("Starting LAMMPS procedure...\n")

    print(os.getcwd())
    if (os.path.abspath(os.getcwd()).split('/'))[-1]!='scripts':
        os.chdir('scripts')
    print(os.getcwd())

    if args.restart:
        routine = 'in.segregation_r'
        struct_flag = ''
    else:
        routine = 'in.segregation'
        struct_flag = f'-var structure_name {structure} '

    restart_flag = True

    while restart_flag:
        task = (f'{lmp} -in  {routine} ' + mu_arg +
                f'-var name {name} ' + 
                struct_flag +
                f'-var conc_f {args.conc} -var kappa_f {args.kappa} ' + 
                f'-pk omp {job} ' +
                f'-sf omp')

        print(task)

        counter = 0
        N_conv = 0
        file_count = args.zero_count
        N_conv_tot = 0
        last_counter = 0
        datfile = ''
        exitflag = False
        
        with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
            time.sleep(0.1)
            print('\n')
            for line in p.stdout:
                if 'ERROR' in line:
                    raise ValueError(f'ERROR in LAMMPS: {line}')
                if 'thermo output file:' in line:
                    src_path = line.split()[-1]
                    src = src_path.split('/')[-1]
                elif "dumpfile" in line:
                    dumpfile = (line.replace('dumpfile ', '')).replace('\n', '')
                elif "datfile" in line:
                    datfile = (line.replace('datfile ', '')).replace('\n', '')
                elif "vcsgc_loop" in line:
                    if restart_flag:
                        restart_flag = False
                    counter += 1
                    print('loop', counter)
                elif "Per-node simulation cell is too small for fix sgcmc" in line:
                    raise ValueError(line)

                if nonverbose:
                    if '!' in line:
                        print(line.replace('!', ''), end='')
                else:
                    print(line, end='')   
                if (counter != last_counter) and (counter%N_loops == 0):
                    last_counter = counter
                    impath = f'../workspace/{name}/images'
                    Path(impath).mkdir(exist_ok=True)  
                    parser_ = argparse.ArgumentParser()
                    plot_args = parser_.parse_args('')
                    fname = f'../workspace/{name}/segregarion_plot.txt'
                    flag1=False
                    flag2=False
                    flag3=False
                    flag4=False
                    flag5=False
                    flag6=False
                    with open(fname, 'r') as f :
                        for line in f:
                            if 'slope width' in line:
                                plot_args.w = int(line.split()[-1])
                                flag1=True
                            if 'step' in line:
                                plot_args.st = int(line.split()[-1])
                                flag2=True
                            if 'rolling mean width' in line:
                                plot_args.num = int(line.split()[-1])
                                flag3=True
                            if 'offset' in line:
                                plot_args.s1 = int(line.split()[-1])
                                flag4=True
                            if 'converged slope' in line:
                                slope_conv = float(line.split()[-1])
                                flag5=True
                            if 'number of points for convergence' in line:
                                N_conv_criteria = int(line.split()[-1])
                                flag6=True
                    flag = (flag1 and flag2 and flag3 and flag4 and flag5 and flag6)
                    if not flag:
                        raise ValueError(f'incorrect segregarion_plot.txt')
                    
                    plot_args.name = args.name
                    plot_args.src = src
                    plot_args.hide = (not args.plot)
                    plot_args.slope_conv = slope_conv
                    plot_args.postfix = args.postfix
                    slope, E_mean = plot(plot_args)
                    slope = np.array(slope)
                    _N_conv_tot = np.sum(np.abs(slope)<=slope_conv)
                    if _N_conv_tot > N_conv_tot:
                        N_conv += (_N_conv_tot-N_conv_tot)
                    N_conv_tot = _N_conv_tot
                    if len(slope)>0:
                        if slope[-1]>slope_conv:
                            N_conv = 0
                        
                    print('convergence criteria achieved in', N_conv, 'points')

                    if N_conv >= N_conv_criteria:
                        if datfile == '':
                            print('Error: unrecognized datfile')
                        else:
                            print(f'saving state for sampling: {file_count+1}')
                            file = datfile.replace("\n", "")
                            outfile = file.replace('.dat', '') + f'_n{file_count}.dat'
                            fpath = f'../workspace/{name}/dat/{file}'  
                            dest = f'../workspace/{name}/samples'
                            Path(dest).mkdir(exist_ok=True)  
                            shutil.copyfile(fpath, f'{dest}/{outfile}')
                            file_count+=1
                            if file_count >= args.samples:
                                exitflag = True
                                p.kill()
                                print('All done!')
        if not exitflag:
            print('\n!!!!!!!!!!!!!!!!!\n\nError occured in LAMMPS')
            if restart_flag:
                raise ValueError('Error in LAMMPS, check input script and log file')
            else:
                print('\n!!!!!!!!!!!!!!!!!\n\nRestarting simulation\n\n!!!!!!!!!!!!!!!!!\n\n')
                restart_flag=True  
                routine = 'in.segregation_r'
                struct_flag = ''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", required=True, help='for example STGB_210')
    parser.add_argument("-s", "--structure", required=False, default=False)
    parser.add_argument("-v", "--verbose", required=False, default=False, action='store_true',
                        help='show LAMMPS outpt')
    parser.add_argument("-r", "--restart", required=False, default=False, action='store_true')
    parser.add_argument("-j", "--job", required=False, default=1)
    parser.add_argument("-m", "--mean-width", dest='mean_width', required=False, default=50)
    parser.add_argument("-c", "--conc", required=False, default=-1, type=float)
    parser.add_argument("--mu", required=False, default=None, type=float)
    parser.add_argument("-k", "--kappa", required=False, default=-1, type=float)
    parser.add_argument("-p", "--plot", required=False, default=False, action='store_true',
                        help='show the thermodynamic plot')
    parser.add_argument("--loops", required=False, default=100, type=int,
                        help='draw the thermodynamic plot each <N> loops')
    parser.add_argument("--samples", required=False, default=100, type=int, help='how many samples to save')
    parser.add_argument("--zero-count", dest='zero_count', required=False, default=0, type=int, help='start numeration of saving samples from this number')
    parser.add_argument("--ovito", required=False, default=False, action='store_true',
                        help='open the dump in ovito')
    parser.add_argument("--postfix", required=False, default='', help="add this postfix at the end of output file's names")
    args = parser.parse_args()
    main(args)




