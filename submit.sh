#!/usr/bin/env bash
name=$1
project=final
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

#python segregation_cooling.py -n ${project} --np 27 -j 3 > workspace/${project}/logs/segregation_cooling.out
#python -u segregation_range_mpi.py -n ${project} --np 27 -j 3 --cs 1,5 --mu 1 --loops 100 --prev cooled > workspace/${project}/logs/segregation_range_${name}.out
#python -u segregation_range_mpi.py -n ${project} --np 27 -j 3 --cs 10,15 --mu 1 --loops 100 --prev cooled > workspace/${project}/logs/segregation_range_${name}.out
#python -u segregation_range_mpi.py -n ${project} --np 27 -j 3 --cs 20,25 --loops 100 > workspace/${project}/logs/segregation_range_${name}.out
python -u segregation_range_mpi.py -n ${project} --np 27 -j 3 --cs 30,35 --loops 100 > workspace/${project}/logs/segregation_range_${name}.out

EOF
module purge
module purge
module load intel
module load openmpi3
module load mkl
module list

sbatch task_${name}_${project}