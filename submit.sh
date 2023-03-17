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

python -u segregation_range_mpi.py -n range1 -r --mu 1.544 --np 27 -j 3 -c 30 -N 31 --samples 5 --loops 30 > $name.out
EOF
sbatch task