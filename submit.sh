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

python -u berendsen_mpi.py -n large --np 64 > $name.out
EOF
sbatch task