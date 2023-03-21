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

python -u segregation_range_mpi.py -n large --mu 1.5 -c 5 -N 10 -k 10 -s berendsen_relax_T300_steps500000.dat --loops 30 --samples 5 --np 27 -j 3 > $name.out
EOF
sbatch task