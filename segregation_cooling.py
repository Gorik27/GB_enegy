from glob import glob
from pathlib import Path
import argparse, os
from subprocess import Popen, PIPE
import time, re, shutil, sys
import numpy as np
sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp
from plot_segregation import main as plot
import logging
from datetime import datetime
now = datetime.now()
current_time = now.strftime("%Y-%m-%d %H:%M:%S")


def main(args):
    nonverbose = (not args.verbose)
    job = args.job
    name = args.name
    structure = args.structure
    N_loops = args.loops
    kappa = args.kappa
    if args.kappa == -1:
        with open(f'workspace/{name}/input.txt', 'r') as f:
            for line in f:
                if 'variable kappa equal' in line:
                    kappa = float(line.split(' ')[-1])
    logname = f'segregation_range_cooled_k_{kappa}'
    logging.basicConfig(filename=f'workspace/{name}/{logname}.log', 
                        encoding='utf-8', 
                        format='%(message)s',
                        level=logging.INFO)

    logging.info(f"""
################
    START
################
{current_time}
################
    """)
    
    if args.mu:
        mu_arg = f'-var mu0 {args.mu} '
    else:
        mu_arg = ''

    print(f'workspace/{name}/dat/segregation_*_k_{float(args.file_kappa)}.dat')
    structures = []
    for filename in glob(f'workspace/{name}/dat/segregation_*_k_{float(args.file_kappa)}.dat'):
        print(filename)   
        structures.append(filename.split('/')[-1])



    print(name, '\n')
    print(structures)
    logging.info(f'{name}\n')
    logging.info(f'{structures}\n')

    print(os.getcwd())
    logging.info(os.getcwd())
    if (os.path.abspath(os.getcwd()).split('/'))[-1]!='scripts':
        os.chdir('scripts')
    print(os.getcwd())
    logging.info(os.getcwd())

    step_ind = 0

    id_file = f'../workspace/{args.name}/dump/CNA/GBs.txt'
    gb_list = np.loadtxt(id_file).astype(int)[:,0]
    gb_list_arg = (''.join(f'{id} 1\n' for id in gb_list))
    gb_list_arg = f'{len(gb_list)}\n{gb_list_arg}'
    gb_list_file = f'../workspace/{args.name}/dump/CNA/GB_group.txt'
    with open(gb_list_file, 'w') as f:
        f.write(gb_list_arg)

    output_file = f"../workspace/{args.name}/segregation_coolded_{args.postfix}.txt"
    if not os.path.isfile(output_file):
        with open(output_file, 'a') as f:
            f.write('segregation range output\n')
            f.write('c,E,mu\n')
    else:
        with open(output_file, 'r') as f:
            lines = f.read().split('\n')
            while '' in lines: lines.remove('')
            print(lines)
            if not 'c,E,mu' in lines[-1]:
                last_point = lines[-1].split(',')
                last_conc = float(last_point[0])
                last_mu = float(last_point[2])
                step_ind = len(lines)-1
                args.restart = True
    conc = float(structures[step_ind].split('_')[1]) 
    structure = structures[step_ind]

    if args.restart:
        routine = 'in.segregation_gb_cooling_r'
        struct_flag = ''
        if mu_arg == '':
            thermo = f"../workspace/{args.name}/thermo_output/segregation_{conc}_k_{args.file_kappa}.txt"
            if os.path.isfile(thermo):
                with open(thermo, 'r') as f:
                    lines = f.read().split('\n')
                    while '' in lines: lines.remove('')
                    if not '#' in lines[-1]:
                        last_mu = float(lines[-1].split('; ')[-1])
            mu_arg = f'-var mu0 {last_mu} '
    else:
        routine = 'in.segregation_gb_cooling'
        

    restart_flag = True

    while restart_flag:
        struct_flag = f'-var structure_name {structure} '
        
        if args.job == 1:
            suffix = ''
        else:
            suffix = f' -sf omp -pk omp {args.job} '
        
        task = (f'mpirun -np {args.np} lmp_intel_cpu_openmpi -in  {routine} ' + mu_arg +
                f'-var name {name} ' + 
                struct_flag + ' ' +
                f'-var gb_list_file {gb_list_file} ' +
                f'-var conc_f {conc} -var kappa_f {args.kappa} ' + 
                suffix)

        msg = task
        print(msg)
        logging.info(msg)

        counter = 0
        last_counter = 0
        exitflag = False
        
        print("Starting LAMMPS procedure...\n")
        logging.info("Starting LAMMPS procedure...\n")

        with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
            time.sleep(0.1)
            print('\n')
            logging.info('\n')
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
                elif "mu = " in line:
                    mu = float((line.replace('\n', '')).split(' ')[-1])
                elif "vcsgc_loop" in line:
                    if restart_flag:
                        restart_flag = False
                    counter += 1
                    msg = f'loop {counter}'
                    print(msg)
                    logging.info(msg)
                elif "Per-node simulation cell is too small for fix sgcmc" in line:
                    raise ValueError(line)
                elif "All done" in line:
                    exitflag = True

                if nonverbose:
                    if '!' in line:
                        msg = line.replace('!', '').replace('\n', '')
                        print(msg)
                        logging.info(msg)
                else:   
                    msg = line.replace('\n', '')
                    print(msg)
                    logging.info(msg)
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
                    with open(fname, 'r') as f :
                        for line in f:
                            if 'slope width' in line:
                                plot_args.w = int(line.split()[-1])
                                flag1=True
                            elif 'step' in line:
                                plot_args.st = int(line.split()[-1])
                                flag2=True
                            elif 'rolling mean width' in line:
                                plot_args.num = int(line.split()[-1])
                                flag3=True
                            elif 'offset' in line:
                                plot_args.s1 = int(line.split()[-1])
                                flag4=True
                            elif 'converged slope' in line:
                                slope_conv = float(line.split()[-1])
                                flag5=True
                    flag = (flag1 and flag2 and flag3 and flag4 and flag5)
                    if not flag:
                        raise ValueError(f'incorrect segregarion_plot.txt')
                    
                    plot_args.name = args.name
                    plot_args.src = src
                    plot_args.hide = (not args.plot)
                    plot_args.slope_conv = slope_conv
                    plot_args.postfix = f'cooling{args.postfix}'
                    plot_args.temp = True
                    slope, E_mean = plot(plot_args) # slope - eV/atom/MC step; E_mean - eV/atom
                    
        if not exitflag:
            msg = '\n!!!!!!!!!!!!!!!!!\n\nError occured in LAMMPS'
            print(msg)
            logging.info(msg) 
            if restart_flag:
                raise ValueError('Error in LAMMPS, check input script and log file')
            else:
                msg = '\n!!!!!!!!!!!!!!!!!\n\nRestarting simulation\n\n!!!!!!!!!!!!!!!!!\n\n'
                print(msg)
                logging.info(msg) 
                restart_flag=True  
                routine = 'in.segregation_gb_cooling_r'
                struct_flag = ''
                mu_arg = f'-var mu0 {mu} '
        else:
            msg = 'success'
            print(msg)
            logging.info(msg) 
            


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", required=True, help='for example STGB_210')
    parser.add_argument("-s", "--structure", required=False, default=False)
    parser.add_argument("-v", "--verbose", required=False, default=False, action='store_true',
                        help='show LAMMPS outpt')
    parser.add_argument("-r", "--restart", required=False, default=False, action='store_true')
    parser.add_argument("-j", "--job", required=False, default=1)
    parser.add_argument("--np", required=False, default=1)
    parser.add_argument("-m", "--mean-width", dest='mean_width', required=False, default=50)
    parser.add_argument("--mu", required=False, default=None, type=float)
    parser.add_argument("-k", "--kappa", required=False, default=-1, type=float)
    parser.add_argument("-p", "--plot", required=False, default=False, action='store_true',
                        help='show the thermodynamic plot')
    parser.add_argument("--loops", required=False, default=100, type=int,
                        help='draw the thermodynamic plot each <N> loops')
    parser.add_argument("--samples", required=False, default=1, type=int, help='how many samples to save')
    parser.add_argument("--zero-count", dest='zero_count', required=False, default=0, type=int, 
                        help='start numeration of saving samples from this number')
    parser.add_argument("--postfix", required=False, default='', help="add this postfix at the end of output file's names")
    parser.add_argument("--fk", dest='file_kappa', required=True, type=float, help="kappa from last step")
    args = parser.parse_args()
    main(args)


