#!/usr/bin/env bash
name=$1
cat > task_$name << EOF
#!/usr/bin/env bash
#SBATCH --nodes=1
#SBATCH --ntasks=94
#SBATCH --job-name=$name

module purge
module load intel
module load openmpi3

#python -u create.py -n $name -j 3 > ${name}_create.out
#python -u berendsen_init_mpi.py -n ${name} -j 3 --np 27 > ${name}_init_berendsen.out
python -u berendsen_mpi.py -n ${name} -j 3 --np 27 > ${name}_berendsen.out
python -u segregation_range_mpi.py -n $name -s berendsen_relax_T300_steps5000000.dat --mu 1.23 -c1 0 -c2 5 -N 12 -k 100 --loops 30 --samples 1 --np 27 -j 3 > ${name}_seg.out
EOF
sbatch task_$name