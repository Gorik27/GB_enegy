#!/usr/bin/env bash
name=$1
cat > task << EOF
#!/usr/bin/env bash
#SBATCH --nodes=1
#SBATCH --ntasks=94
#SBATCH --job-name=$name

module purge
module load intel
module load openmpi3

python -u berendsen_mpi.py -n 5g --heat --T0  300 -s berendsen_relax_T300_steps5000000.dat --np 27 -j 3 > $name.out
python -u segregation_range_mpi.py -n 5g -s berendsen_relax_T600_steps5000000.dat --mu 1.23 -c1 0 -c2 5 -N 10 -k 100 --loops 30 --samples 5 --np 27 -j 3 > $name.out
EOF
sbatch task