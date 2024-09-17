#!/usr/bin/env bash
name=$1
cat > task_${name} << EOF
#!/usr/bin/env bash
#SBATCH --nodes=1
#SBATCH --ntasks=94
#SBATCH --job-name=$name

module purge
module purge
module load intel
module load openmpi3
module load mkl
module list

mpirun --bind-to core -np 94 pw.x -pd .true. -inp ${name}.in > ${name}.out
EOF
module purge
module purge
module load intel
module load openmpi3
module load mkl
module list

sbatch task