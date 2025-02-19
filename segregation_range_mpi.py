from pathlib import Path
import argparse, os
from subprocess import Popen, PIPE
import time, re, shutil, sys
import numpy as np
sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp
from plot_segregation import main as plot
import logging
from collections.abc import Iterable
from datetime import datetime
now = datetime.now()
current_time = now.strftime("%Y-%m-%d %H:%M:%S")

def list_of_floats(arg):
    return list(map(float, arg.split(',')))

def log(*msg):
    print(*msg)
    if isinstance(msg, Iterable):
        time = datetime.now().strftime("%H:%M")
        logging.info(f'[{time}]     '+' '.join(map(str, msg)))
    else:
        logging.info(f'[{time}]     '+str(msg))

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True, help='for example STGB_210')
parser.add_argument("-s", "--structure", required=False, default=False)
parser.add_argument("-v", "--verbose", required=False, default=False, action='store_true',
                    help='show LAMMPS outpt')
parser.add_argument("-r", "--restart", required=False, default=False, action='store_true')
parser.add_argument("-j", "--job", required=False, default=1)
parser.add_argument("--np", required=False, default=1)
parser.add_argument("-c1", "--conc1", help='min concentration', required=False, type=float)
parser.add_argument("-c2", "--conc2", help='max concentration', required=False, type=float)
parser.add_argument("-N", "--conc-num", dest='conc_num', required=False, type=int)
parser.add_argument("--cs", dest='conc_list', required=False, type=list_of_floats)
parser.add_argument("--mu", required=False, default=None, type=float)
parser.add_argument("-k", "--kappa", required=False, default=-1, type=float)
parser.add_argument("--loops", required=False, default=100, type=int,
                    help='draw the thermodynamic plot each <N> loops')
parser.add_argument("--samples", required=False, default=1, type=int, help='how many samples to save')
parser.add_argument("--zero-count", dest='zero_count', required=False, default=0, type=int, 
                    help='start numeration of saving samples from this number')
parser.add_argument("-p", "--postfix", required=False, default='', help="add this postfix at the end of output file's names")
parser.add_argument("--prev", dest='previous', default='berendsen', required=False, 
help='tag of previous step in conf.txt: "berendsen"; "cooled"')
args = parser.parse_args()

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
if int(kappa)==kappa:
    kappa = int(kappa)
if args.conc_list:
    logname = f'segregation_range_cs_{args.conc_list}_k_{kappa}'
else:
    logname = f'segregation_range_c_{args.conc1}_{args.conc2}_N_{args.conc_num}_k_{kappa}'
logging.basicConfig(filename=f'workspace/{name}/{logname}.log', 
                    encoding='utf-8', 
                    format='%(message)s',
                    level=logging.INFO)

log(f"""
################
START
################
{current_time}
################
""")

if (os.path.abspath(os.getcwd()).split('/'))[-1]!='scripts':
    os.chdir('scripts')

if args.conc_list:
    conc_range = args.conc_list
else:
    conc_range = np.linspace(args.conc1, args.conc2, num=args.conc_num)
step_ind = 0

if args.conc_list:
    output_file = f"../workspace/{args.name}/segregation_range_cs_{args.conc_list}_{args.postfix}.txt"
else:
    output_file = f"../workspace/{args.name}/segregation_range_c_{args.conc1}_{args.conc2}_n_{args.conc_num}_{args.postfix}.txt"
continue_flag = False
if not os.path.isfile(output_file):
    with open(output_file, 'a') as f:
        f.write('segregation range output\n')
        f.write('c,E,mu\n')
else:
    with open(output_file, 'r') as f:
        lines = f.read().split('\n')
        while '' in lines: lines.remove('')
        if not 'c,E,mu' in lines[-1]:
            last_point = lines[-1].split(',')
            last_conc = float(last_point[0])
            last_mu = float(last_point[2])
            step_ind = np.where(conc_range==last_conc)[0][0]+1
            if int(last_conc)==last_conc:
                last_conc = int(last_conc)
            structure = f'segregation_{last_conc}_k_{kappa}.dat'
            continue_flag = True

if conc_range[step_ind] == int(conc_range[step_ind]):
    conc_range_i = int(conc_range[step_ind])
else:
    conc_range_i = conc_range[step_ind]

thermo = f"../workspace/{args.name}/thermo_output/segregation_gb_{conc_range_i}_k_{kappa}.txt"
thermo2 = f"../workspace/{args.name}/thermo_output/segregation_{conc_range_i}_k_{kappa}.txt"

if os.path.isfile(thermo):
    restart = True
    log('restart')
    log(thermo)
elif os.path.isfile(thermo2):
    restart = True
    log('restart')
    thermo = thermo2
    log(thermo)
else:
    restart = False

if not structure and not restart:
    fname = f'../workspace/{name}/conf.txt'
    flag=False
    with open(fname, 'r') as f :
        for line in f:
            if args.previous in line:
                structure = line.split()[-1]
                log(f'Structure {structure} used')
                flag = True
    if not flag:
        raise ValueError(f'cannot find structure with tag {args.previous} in conf.txt (see "{fname[3:]}"')
    
if args.mu:
    mu_arg = f'-var mu0 {args.mu} '
else:
    mu_arg = ''

if restart:
    routine = 'in.segregation_gb_r'
    struct_flag = ''
    if mu_arg == '':
        flag = False
        if os.path.isfile(thermo):
            with open(thermo, 'r') as f:
                lines = f.read().split('\n')
                while '' in lines: lines.remove('')
                if not '#' in lines[-1]:
                    last_mu = float(lines[-1].split('; ')[-1])
                    mu_arg = f'-var mu0 {last_mu} '
                    flag = True
        if (not flag) and continue_flag:
            mu_arg = f'-var mu0 {last_mu} '
else:
    routine = 'in.segregation_gb'
    struct_flag = f'-var structure_name {structure} '


restart_flag = True

while restart_flag:
    log(
f"""
    
#### NEW STEP ####
    
C = {conc_range[step_ind]} 
step = {step_ind}/{len(conc_range)}

##################
""")
    if job == 1:
        suffix = ''
    else:
        suffix = f' -sf omp -pk omp {job} '
    
    task = (f'mpirun --bind-to core -np {args.np} lmp_intel_cpu_openmpi -in  {routine} ' + mu_arg +
            f'-var name {name} ' + 
            struct_flag + ' ' +
            f'-var conc_f {conc_range[step_ind]} -var kappa_f {args.kappa} ' + 
            suffix)

    counter = 0
    file_count = args.zero_count
    last_counter = 0
    datfile = ''
    exitflag = False
    
    log("Starting LAMMPS procedure...\n")
    log(task)

    with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
        time.sleep(0.1)
        log('\n')
        for line in p.stdout:
            if 'ERROR' in line:
                raise ValueError(f'ERROR in LAMMPS: {line}\nsee "workspace/{args.name}/logs/{routine.replace("in.", "")}.log"')
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
                log(f'loop {counter}')
            elif "Per-node simulation cell is too small for fix sgcmc" in line:
                raise ValueError(line)
            if nonverbose:
                if '!' in line:
                    log(line.replace('!', '').replace('\n', ''))
            else:   
                log(line.replace('\n', ''))
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
                plot_args.temp = False
                plot_args.hide = True
                plot_args.slope_conv = slope_conv
                plot_args.postfix = args.postfix
                slope, E_mean = plot(plot_args) # slope - eV/atom/MC step; E_mean - eV/atom
                slope = np.array(slope)
                if len(slope)>0:
                    if slope[-1]<slope_conv:
                        N_conv = 0
                        for i in range(0, len(slope)):
                            if np.abs(slope[-1-i]) <= slope_conv:
                                    N_conv += 1
                            else: 
                                break
                else:
                    N_conv = 0
                    
                log(f'convergence criteria achieved in {N_conv} points')

                if N_conv >= N_conv_criteria:
                    if datfile == '':
                        log('Error: unrecognized datfile')
                    else:
                        log(f'saving state for sampling: {file_count+1}')
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
                            log(f'Step done!\nE {E_mean}\nmu {mu}')
                            if args.conc_list:
                                output_file = f"../workspace/{args.name}/segregation_range_cs_{args.conc_list}_{args.postfix}.txt"
                            else:
                                output_file = f"../workspace/{args.name}/segregation_range_c_{args.conc1}_{args.conc2}_n_{args.conc_num}_{args.postfix}.txt"
                            with open(output_file, 'a') as f:
                                f.write(f'{conc_range[step_ind]},{E_mean},{mu}\n')
    if not exitflag:
        log('\n!!!!!!!!!!!!!!!!!\n\nError occured in LAMMPS')
        if restart_flag:
            raise ValueError(f'Error in LAMMPS, check input script and log file, see "workspace/{args.name}/logs/{routine.replace("in.", "")}.log"')
        else:
            log('\n!!!!!!!!!!!!!!!!!\n\nRestarting simulation\n\n!!!!!!!!!!!!!!!!!\n\n')
            restart_flag=True  
            routine = 'in.segregation_gb_r'
            struct_flag = ''
            mu_arg = f'-var mu0 {mu} '
    else:
        log('success')
        step_ind += 1
        restart_flag=True  
        routine = 'in.segregation_gb'
        struct_flag = f'-var structure_name {datfile}'
        if step_ind >= len(conc_range):
            log('All done')
            break





