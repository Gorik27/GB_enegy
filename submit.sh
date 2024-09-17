#!/usr/bin/env bash
name=$1
project=final2
cat > task_${name}_${project} << EOF
#!/usr/bin/env bash
#SBATCH --nodes=1
#SBATCH --ntasks=94
#SBATCH --job-name=${name}_${project}

module purge
module purge
module load intel
module load openmpi3
module load mkl
module list

python segregation_cooling.py -n ${project} --np 27 -j 3 > workspace/${project}/logs/segregation_cooling.out
EOF
module purge
module purge
module load intel
module load openmpi3
module load mkl
module list

sbatch task_${name}_${project}