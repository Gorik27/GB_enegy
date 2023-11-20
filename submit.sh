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

#python -u berendsen_init_mpi.py -n ${name} -j 3 --np 27 > ${name}_init_berendsen.out
#python -u berendsen_mpi.py -n ${name} -j 3 --np 27 > ${name}_berendsen_relax.out
#python -u cooling_mpi.py -n ${name} -j 3 --np 27 > ${name}_cooling.out
#python -u minimize.py -n ${name} -j 3 --np 27 > ${name}_minimizing.out
#python -u spectrum.py -n ${name} -j 3 --np 27 > ${name}_spectrum.out
#python -u spectrum_read.py -n ${name} -j 3 --np 27 > ${name}_spectrum_read.out
python -u spectrum2.py -n ${name} -j 3 --np 27 > ${name}_spectrum2.out
EOF
sbatch task_$name