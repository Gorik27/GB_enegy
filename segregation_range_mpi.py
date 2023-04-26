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
        with open(f'workspace/{args.name}/input.txt', 'r') as f:
            for line in f:
                if 'variable kappa equal' in line:
                    kappa = float(line.split(' ')[-1])
    logname = f'segregation_range_c_{args.conc1}_{args.conc2}_N_{args.conc_num}_k_{kappa}'
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
    
    if not structure and not args.restart:
        fname = f'workspace/{name}/conf.txt'
        flag=False
        with open(fname, 'r') as f :
            for line in f:
                if 'berendsen' in line:
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
    logging.info(f'{name}\n')

    print(os.getcwd())
    logging.info(os.getcwd())
    if (os.path.abspath(os.getcwd()).split('/'))[-1]!='scripts':
        os.chdir('scripts')
    print(os.getcwd())
    logging.info(os.getcwd())

    conc_range = np.linspace(args.conc1, args.conc2, num=args.conc_num)
    step_ind = 0

    output_file = f"../workspace/{args.name}/segregation_range_c_{args.conc1}_{args.conc2}_n_{args.conc_num}_{args.postfix}.txt"
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
                step_ind = np.where(conc_range==last_conc)[0][0]+1
                args.restart = True

    if args.restart:
        routine = 'in.segregation_r'
        struct_flag = ''
        if mu_arg == '':
            thermo = f"../workspace/{args.name}/thermo_output/segregation_{conc_range[step_ind]}_k_{kappa}.txt"
            if os.path.isfile(thermo):
                with open(thermo, 'r') as f:
                    lines = f.read().split('\n')
                    while '' in lines: lines.remove('')
                    if not '#' in lines[-1]:
                        last_mu = float(lines[-1].split('; ')[-1])
            mu_arg = f'-var mu0 {last_mu} '
    else:
        routine = 'in.segregation'
        struct_flag = f'-var structure_name {structure} '

    restart_flag = True

    while restart_flag:
        msg = (
f"""
        
#### NEW STEP ####
        
C = {conc_range[step_ind]} 
step = {step_ind}/{args.conc_num}

##################
""")
        print(msg)
        logging.info(msg)
        if args.job == 1:
            suffix = ''
        else:
            suffix = f' -sf omp -pk omp {args.job} '
        
        task = (f'mpirun -np {args.np} lmp_intel_cpu_openmpi -in  {routine} ' + mu_arg +
                f'-var name {name} ' + 
                struct_flag +
                f'-var conc_f {conc_range[step_ind]} -var kappa_f {args.kappa} ' + 
                suffix)

        msg = task
        print(msg)
        logging.info(msg)

        counter = 0
        N_conv = 0
        file_count = args.zero_count
        N_conv_tot = 0
        last_counter = 0
        datfile = ''
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
                        
                    msg = f'convergence criteria achieved in {N_conv} points'
                    print(msg)
                    logging.info(msg) 

                    if N_conv >= N_conv_criteria:
                        if datfile == '':
                            msg = 'Error: unrecognized datfile'
                            print(msg)
                            logging.info(msg) 
                        else:
                            msg = f'saving state for sampling: {file_count+1}'
                            print(msg)
                            logging.info(msg) 
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
                                mu_arg = f'-var mu0 {mu} '
                                msg = f'Step done!\nE {E_mean}\nmu {mu}'
                                print(msg)
                                logging.info(msg) 
                                output_file = f"../workspace/{args.name}/segregation_range_c_{args.conc1}_{args.conc2}_n_{args.conc_num}_{args.postfix}.txt"
                                with open(output_file, 'a') as f:
                                    f.write(f'{conc_range[step_ind]},{E_mean},{mu}\n')
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
                routine = 'in.segregation_r'
                struct_flag = ''
                mu_arg = f'-var mu0 {mu} '
        else:
            msg = 'success'
            print(msg)
            logging.info(msg) 
            step_ind += 1
            restart_flag=True  
            routine = 'in.segregation_r'
            struct_flag = ''
            if step_ind >= args.conc_num:
                msg = 'All done'
                print(msg)
                logging.info(msg) 
                break


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
    parser.add_argument("-c1", "--conc1", help='min concentration', required=True, type=float)
    parser.add_argument("-c2", "--conc2", help='max concentration', required=True, type=float)
    parser.add_argument("-N", "--conc-num", dest='conc_num', required=True, type=int)
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
    parser.add_argument("--thermo", required=False, default='berendsen_relax')
    args = parser.parse_args()
    main(args)




