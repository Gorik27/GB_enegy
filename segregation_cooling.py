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
from collections.abc import Iterable
now = datetime.now()
current_time = now.strftime("%Y-%m-%d %H:%M:%S")

def log(*msg):
    print(*msg)
    if isinstance(msg, Iterable):
        logging.info(' '.join(map(str, msg)))
    else:
        logging.info(str(msg))
    
def select_job_partition(args, structures):
    N = len(structures)
    if args.select:
        if args.task != '1_1':
            log("""
!!!!!!!!!!!!!!!!!          WARNING          !!!!!!!!!!!!!!!!!!

    Argumet --task will be ignored since --select is used  
                
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
""")
        conc = list(map(float, args.select))
        _structures = []
        for s in structures:
            if float(s.split('_')[1]) in conc:
                _structures.append(s)
        structures = _structures
        log('Selected files:', str(structures))
    else:
        rank, ntasks = map(int, args.task.split('_'))
        assert rank <= ntasks
        assert rank > 0
        assert ntasks > 0

        if ntasks>1:
            mask = (np.arange(N)%ntasks==(rank-1)).astype(bool)
            structures = list(np.array(structures)[mask])
            log('Rank:', rank, '    Total tasks: ', ntasks)
            log('Selected files:', str(structures))
        conc = [float(s.split('_')[1]) for s in structures]
    return conc, structures
    

parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True, help='for example STGB_210')
parser.add_argument("-s", "--structure", required=False, default=False)
parser.add_argument("-v", "--verbose", required=False, default=False, action='store_true',
                    help='show LAMMPS outpt')
parser.add_argument("-r", "--restart", required=False, default=False, action='store_true')
parser.add_argument("-j", "--job", required=False, default=1)
parser.add_argument("--task", required=False, default="1_1", 
                    help='"n_m": do n-th job from m jobs')
parser.add_argument("--select", required=False, default=[], nargs='+',
                    help='instead of using --task, this argument allow to explisitly select concentrations')
parser.add_argument("--np", required=False, default=1)
parser.add_argument("-m", "--mean-width", dest='mean_width', required=False, default=50)
parser.add_argument("--mu", required=False, default=None, type=float)
parser.add_argument("-k", "--kappa", required=False, default=-1, type=float)
parser.add_argument("-p", "--plot", required=False, default=False, action='store_true',
                    help='show the thermodynamic plot')
parser.add_argument("--loops", required=False, default=100, type=int, dest='N_loops',
                    help='draw the thermodynamic plot each <N> loops')
parser.add_argument("--postfix", required=False, default='', help="add this postfix at the end of output file's names")
parser.add_argument("--save", required=False, default=False, action='store_true',
                     help='make save of cooling step if it has not finished')
args = parser.parse_args()

name = args.name

if args.select:
    tasklabel = 'conc'+('_'.join(args.select))
else:
    tasklabel = args.task
logname = 'segregation_range_cooled_'+tasklabel
print(logname+'.log')
logging.basicConfig(filename=f'workspace/{name}/logs/{logname}.log', 
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

# selecting structure files, jobs spreading between tasks 
structures = []
for filename in glob(f'workspace/{name}/dat/segregation_[0-9]*.dat'):
        if not 'copy' in filename:
            structures.append(filename.split('/')[-1])

log('All files (unsorted):', str(structures))
structures = sorted(structures,
                    key=(lambda s: float(s.split('_')[1])))

log('All files:', str(structures))

concs, structures = select_job_partition(args, structures)

# change directory
if (os.path.abspath(os.getcwd()).split('/'))[-1]!='scripts':
    os.chdir('scripts')

# output file; select files that has not been calculated
output_file = f"../workspace/{args.name}/segregation_coolded_{tasklabel}{args.postfix}.txt"
if not os.path.isfile(output_file):
    with open(output_file, 'a') as f:
        f.write('#segregation cooling output\n')
        f.write('c,cavg,E,mu\n')
else:
    with open(output_file, 'r') as f:
        lines = f.read().split('\n')
        while '' in lines: lines.remove('')
        for line in lines:
            if not 'c,cavg,E,mu' in line and not '#' in line:
                point = line.split(',')
                conc = float(point[0])
                cavg = float(point[1])
                mu = float(point[3])
                if conc in concs:
                    i = concs.index(conc)
                    concs.remove(conc)
                    log(structures[i], 'is already calculated')
                    structures.remove(structures[i])
                    
log('Files to be calculated:', structures)



# routine

restart = False 

if args.job == 1:
    suffix = ''
else:
    suffix = f' -sf omp -pk omp {args.job} '

for i, structure in enumerate(structures):
    struct_flag = f'-var structure_name {structure} '

    if args.kappa == -1:
        kappa = float(structure.split('_')[-1].replace('.dat', ''))
    else:
        kappa = args.kappa
    if kappa==int(kappa):
        kappa = int(kappa)

    mu_arg = args.mu
    if not mu_arg:
        conc = structure.split('_')[-3]
        segrange_file = f"../workspace/{args.name}/thermo_output/segregation_cooling_{tasklabel}_{conc}_k_{kappa}.txt"
        print(segrange_file)
        if os.path.isfile(segrange_file):
            thermo = glob(segrange_file)[0]
            restart = True
        else:
            thermo = glob(f"../workspace/{args.name}/thermo_output/segregation_{conc}_k_{kappa}.txt")[0]
        log(f'Termo file: {thermo}')
        if os.path.isfile(thermo):
            with open(thermo, 'r') as f:
                lines = f.read().split('\n')
                while '' in lines: lines.remove('')
                if not '#' in lines[-1]:
                    last_mu = float(lines[-1].split('; ')[-1])
        else:
            last_mu = 1
        mu_arg = f'-var mu0 {last_mu} '
    
    # restart
    if restart:
        routine = 'in.segregation_gb_cooling_r'
    else:
        routine = 'in.segregation_gb_cooling'

    conc = concs[i]
        
    restart_flag = True
    
    while restart_flag:
        if args.save:
            task = (f'mpirun -np {args.np} {lmp} -in in.savedat_segregation_gb_cooling ' + mu_arg +
                    f'-var name {name} ' + 
                    struct_flag + ' ' +
                    f'-var conc_f {conc} -var kappa_f {kappa} ' + 
                    f'-var postfix {tasklabel}' + 
                    suffix)
        else:
            task = (f'mpirun -np {args.np} {lmp} -in {routine} ' + mu_arg +
                    f'-var name {name} ' + 
                    struct_flag + ' ' +
                    f'-var conc_f {conc} -var kappa_f {kappa} ' + 
                    f'-var postfix {tasklabel}' + 
                    suffix)
                
        counter = 0
        last_counter = 0
        exitflag = False
        
        log("Starting LAMMPS procedure...\n")
        log(task)

        with Popen(task.split(), stdout=PIPE, bufsize=1, universal_newlines=True) as p:
            time.sleep(0.1)
            log('\n')
            for line in p.stdout:
                if 'ERROR' in line:
                    raise ValueError(f'ERROR in LAMMPS: {line}, see "workspace/{args.name}/logs/{routine.replace("in.", "")}.log"')
                if 'thermo output file:' in line:
                    src_path = line.split()[-1]
                    src = src_path.split('/')[-1]
                elif "dumpfile" in line:
                    dumpfile = (line.replace('dumpfile ', '')).replace('\n', '')
                elif "datfile" in line:
                    datfile = (line.replace('datfile ', '')).replace('\n', '')
                elif "mu = " in line:
                    mu = float((line.replace('\n', '')).split(' ')[-1])
                elif "avg_conc = " in line:
                    avg_conc = float((line.replace('\n', '')).split(' ')[-1])
                elif "vcsgc_loop" in line:
                    if restart_flag:
                        restart_flag = False
                    counter += 1
                    log(f'loop {counter}')
                elif "Per-node simulation cell is too small for fix sgcmc" in line:
                    raise ValueError(line)
                elif "All done" in line:
                    exitflag = True

                if not args.verbose:
                    if '!' in line:
                        log(line.replace('!', '').replace('\n', ''))
                else:   
                    log(line.replace('\n', ''))
                if (counter != last_counter) and (counter%args.N_loops == 0):
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
            log('\n!!!!!!!!!!!!!!!!!\n\nError occured in LAMMPS') 
            if restart_flag:
                raise ValueError('Error in LAMMPS, check input script and log file')
            else:
                log('\n!!!!!!!!!!!!!!!!!\n\nRestarting simulation\n\n!!!!!!!!!!!!!!!!!\n\n') 
                restart_flag=True  
                routine = 'in.segregation_gb_cooling_r'
                struct_flag = ''
                mu_arg = f'-var mu0 {mu} '
        else:
            log('success') 
            if not args.save:
                with open(output_file, 'w') as f:
                    f.write(f'{conc},{avg_conc},{E_mean},{mu}\n')