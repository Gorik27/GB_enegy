#!/usr/bin/env python3
"""
Script for calculating segregation energies in a polycrystal using LAMMPS.
Parallel mode: multiple LAMMPS jobs launched simultaneously, each on a single core.
Results are saved incrementally for restart capability.
"""

from pathlib import Path
import argparse
import os
import sys
import subprocess
import time
import numpy as np
from multiprocessing import Pool
import tempfile
import atexit
import signal
import shutil

# Add scripts directory to path and import LAMMPS executable path
sys.path.insert(1, f'{sys.path[0]}/scripts')
from set_lammps import lmp   # lmp is a string with the path to the LAMMPS executable

# Global cleanup registry
temp_dirs = []

def cleanup_temp_dirs():
    """Remove all temporary directories on exit"""
    for d in temp_dirs:
        try:
            shutil.rmtree(d)
        except:
            pass

atexit.register(cleanup_temp_dirs)

# Handle SIGINT gracefully
def signal_handler(sig, frame):
    print("\nInterrupted. Cleaning up...")
    cleanup_temp_dirs()
    sys.exit(1)

signal.signal(signal.SIGINT, signal_handler)

# ----------------------------------------------------------------------
# Argument parsing
# ----------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("-n", "--name", required=True, help="workspace name")
parser.add_argument("-p", "--parallel", type=int, default=1,
                    help="number of parallel LAMMPS jobs (each on 1 core)")
parser.add_argument("-s", "--structure", help="structure name (if not given, read from conf.txt)")
parser.add_argument("-v", "--verbose", action='store_true', default=False,
                    help="print detailed progress information")
parser.add_argument("-f", "--force", action='store_true', default=False,
                    help="ignore existing results and restart calculations from scratch")
parser.add_argument("--max-retries", type=int, default=3,
                    help="maximum number of retries for failed calculations")
args = parser.parse_args()

# Change to scripts directory (all LAMMPS input files are assumed to be there)
os.chdir('scripts')
print(f"Working directory: {os.getcwd()}")

# ----------------------------------------------------------------------
# Determine structure name
# ----------------------------------------------------------------------
structure = args.structure
if not structure:
    fname = f'../workspace/{args.name}/conf.txt'
    if not os.path.isfile(fname):
        raise ValueError(f"Configuration file not found: {fname}")
    
    found = False
    with open(fname, 'r') as f:
        for line in f:
            if 'ann_minimized' in line:
                structure = line.split()[-1]
                print(f"Found structure: {structure}")
                found = True
    if not found:
        raise ValueError(f"Cannot find structure in {fname}")

# ----------------------------------------------------------------------
# Read grain boundary node IDs
# ----------------------------------------------------------------------
id_file = f'../workspace/{args.name}/dump/CNA/GBs.txt'
if not os.path.isfile(id_file):
    raise ValueError(f"GB IDs file not found: {id_file}")

selected = np.loadtxt(id_file).astype(int)
ids = selected[:, 0]   # list of GB node IDs
cna_values = selected[:, 1] if selected.shape[1] > 1 else np.zeros_like(ids)

print(f"Total GB nodes: {len(ids)}")

# ----------------------------------------------------------------------
# Load/save results with locking to avoid corruption
# ----------------------------------------------------------------------
outname = f'../workspace/{args.name}/dump/CNA/GBEs.txt'
lockname = outname + '.lock'

def save_results(results_dict):
    """Save results to file with atomic write"""
    # Create temporary file
    temp_out = outname + '.tmp'
    
    # Prepare output array in original order
    out_array = np.zeros((len(ids), 2))
    for i, id in enumerate(ids):
        out_array[i, 0] = id
        out_array[i, 1] = results_dict.get(id, np.nan)
    
    # Write to temporary file
    np.savetxt(temp_out, out_array, header='id E', fmt='%d %.10f')
    
    # Atomic rename
    os.replace(temp_out, outname)
    
    if args.verbose:
        print(f"Results saved to {outname}")

def load_results():
    """Load existing results, return dict id->E"""
    if not os.path.isfile(outname) or args.force:
        return {}
    
    try:
        data = np.loadtxt(outname)
        if data.size == 0:
            return {}
        if data.ndim == 1:  # only one line
            return {int(data[0]): data[1]}
        else:
            return {int(row[0]): row[1] for row in data if not np.isnan(row[1])}
    except Exception as e:
        print(f"Warning: Could not load existing results: {e}")
        return {}

# Load existing results
existing_results = load_results()
print(f"Found existing results for {len(existing_results)} nodes.")

# Determine which IDs still need to be processed
if args.force:
    ids_to_compute = list(ids)
    print("Force mode: recomputing all nodes")
else:
    ids_to_compute = [id for id in ids if id not in existing_results]
    print(f"Nodes to compute: {len(ids_to_compute)}")

if len(ids_to_compute) == 0:
    print("All nodes already computed. Exiting.")
    sys.exit(0)

# ----------------------------------------------------------------------
# Function to run LAMMPS for a single ID in an isolated directory
# ----------------------------------------------------------------------
def run_one(args_tuple):
    """
    Run LAMMPS for a single GB node ID in its own temporary directory.
    Returns dict with results or error information.
    """
    idx, id, cna, retry_count = args_tuple
    
    # Create unique temporary directory for this job
    temp_dir = tempfile.mkdtemp(prefix=f"lammps_{id}_", dir=os.getcwd())
    temp_dirs.append(temp_dir)  # register for cleanup
    
    # Copy necessary input files to temp directory
    input_files = ['in.seg_minimize_p']
    for f in input_files:
        src = os.path.join(os.getcwd(), f)
        dst = os.path.join(temp_dir, f)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
        elif args.verbose:
            print(f"Warning: Input file {f} not found in scripts directory")
    
    # Command: single MPI process, log to unique file in temp dir
    log_file = f"log_{id}.lammps"
    socket = idx%2
    command = f"numactl --cpunodebind={socket} --membind={socket} mpirun -np 1 --bind-to none  {lmp} -in in.seg_minimize_p -var name {args.name} -var structure_name {structure} -var tmp_script_dir {temp_dir} -var id {id} -log {log_file}"
    #print(command)
    if args.verbose:
        print(f"  [Job {id}] Starting in {temp_dir}")
    
    try:
        # Run LAMMPS in temp directory
        proc = subprocess.Popen(command.split(),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True,
                                cwd=temp_dir)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            error_msg = f"LAMMPS exited with code {proc.returncode}"
            
            # Capture stderr which often contains the actual error
            lammps_error = stderr if stderr else ""
            
            # Also check log file if it exists and has content beyond header
            log_path = os.path.join(temp_dir, log_file)
            if os.path.isfile(log_path) and os.path.getsize(log_path) > 100:  # More than just header
                with open(log_path, 'r') as f:
                    log_content = f.read()
                    if "ERROR" in log_content or "ERROR:" in log_content:
                        lammps_error += "\n" + log_content
            
            # Always show error
            print(f"\n  [Job {id}] LAMMPS FAILED with code {proc.returncode}")
            if lammps_error:
                print("-" * 40)
                print("STDERR/ERROR output:")
                error_lines = lammps_error.strip().split('\n')
                # Show lines containing ERROR or the last 10 lines
                error_lines = [line for line in error_lines if "ERROR" in line or line.strip()] 
                if error_lines:
                    for line in error_lines[-10:]:
                        print(f"  {line}")
                else:
                    # If no error lines found, show last 5 lines of stderr
                    for line in lammps_error.strip().split('\n')[-5:]:
                        print(f"  {line}")
                print("-" * 40)
            else:
                print("  (no error output captured)")
            
            return {"id": id, "cna": cna, "E": np.nan, "db": 0, 
                    "error": error_msg, "stderr": lammps_error[:500], 'socket':socket}
        
        # Parse output for energy and dangerous builds
        db = 0
        E = None
        all_done = False
        
        # Also check log file if stdout doesn't have everything
        log_path = os.path.join(temp_dir, log_file)
        log_content = ""
        if os.path.isfile(log_path):
            with open(log_path, 'r') as f:
                log_content = f.read()
        
        # Parse both stdout and log
        for text in [stdout, log_content]:
            for line in text.split('\n'):
                if "Dangerous builds" in line:
                    try:
                        db = int(line.split()[-1])
                    except:
                        pass
                elif "Seg energy" in line:
                    try:
                        E = float(line.replace('Seg energy ', '').strip())
                    except:
                        pass
                elif "All done" in line:
                    all_done = True
        
        if not all_done:
            if retry_count < args.max_retries:
                return {"id": id, "cna": cna, "retry": True, "retry_count": retry_count + 1,
                        "error": "All done message not found", 'socket':socket}
            else:
                return {"id": id, "cna": cna, "E": np.nan, "db": db, 
                        "error": f"Max retries ({args.max_retries}) exceeded", 'socket':socket}
        
        if E is None:
            if retry_count < args.max_retries:
                return {"id": id, "cna": cna, "retry": True, "retry_count": retry_count + 1,
                        "error": "Seg energy not found", 'socket':socket}
            else:
                return {"id": id, "cna": cna, "E": np.nan, "db": db,
                        "error": f"Max retries ({args.max_retries}) exceeded", 'socket':socket}
        
        if args.verbose:
            print(f"  [Job {id}] Completed: E = {E:.6f}" + 
                  (f" (dangerous builds: {db})" if db > 0 else ""))
        
        return {"id": id, "cna": cna, "E": E, "db": db, "error": None, 'socket':socket}
        
    except subprocess.TimeoutExpired:
        proc.kill()
        if retry_count < args.max_retries:
            return {"id": id, "cna": cna, "retry": True, "retry_count": retry_count + 1,
                    "error": "Timeout"}
        else:
            return {"id": id, "cna": cna, "E": np.nan, "db": 0,
                    "error": f"Timeout after {args.max_retries} retries"}
                    
    except Exception as e:
        # Try to read log file even if LAMMPS crashed
        lammps_error = ""
        log_path = os.path.join(temp_dir, log_file)
        if os.path.isfile(log_path):
            with open(log_path, 'r') as f:
                lammps_error = f.read()
        
        if lammps_error:
            print(f"\n  [Job {id}] LAMMPS ERROR:")
            print("-" * 40)
            error_lines = lammps_error.strip().split('\n')[-20:]
            for line in error_lines:
                print(f"  {line}")
            print("-" * 40)
        
        if retry_count < args.max_retries:
            return {"id": id, "cna": cna, "retry": True, "retry_count": retry_count + 1,
                    "error": str(e)}
        else:
            return {"id": id, "cna": cna, "E": np.nan, "db": 0,
                    "error": f"Exception after {args.max_retries} retries: {str(e)}"}

# ----------------------------------------------------------------------
# Main parallel execution loop with retries
# ----------------------------------------------------------------------
print(f"\nStarting parallel calculations with {args.parallel} concurrent jobs")
print(f"Max retries per job: {args.max_retries}")
print("-" * 50)

# Prepare job list with retry counters
jobs = [(i, id, cna_values[i], 0) for i, id in enumerate(ids) if id in ids_to_compute]
results_dict = existing_results.copy()
failed_jobs = []

# Process jobs with retries
while jobs:
    # Create pool and run jobs
    pool = Pool(processes=min(args.parallel, len(jobs)))
    
    try:
        # Run jobs and collect results as they complete
        completed = 0
        new_results = []
        
        for res in pool.imap_unordered(run_one, jobs):
            completed += 1
            
            if res.get('retry', False):
                # Job needs retry
                failed_jobs.append((res['socket'], res['id'], 0, res['retry_count']))
                print(f"[{completed}/{len(jobs)}] ID {res['id']} failed, will retry (attempt {res['retry_count']})")
            elif res['error']:
                # Permanent failure
                failed_jobs.append((res['socket'], res['id'], res['error'], -1))
                print(f"[{completed}/{len(jobs)}] ID {res['id']} FAILED: {res['error']}")
                results_dict[res['id']] = np.nan
            else:
                # Success
                print(f"[{completed}/{len(jobs)}] ID {res['id']} done, E = {res['E']:.6f}" +
                      (f" (dangerous builds: {res['db']})" if res['db'] > 0 else ""))
                results_dict[res['id']] = res['E']
                new_results.append(res)
            
            # Save results incrementally after each batch
            if len(new_results) >= 5:  # Save every 5 successful jobs
                save_results(results_dict)
                new_results = []
        
        pool.close()
        pool.join()
        
        # Save after all jobs in this batch
        save_results(results_dict)
        
    except KeyboardInterrupt:
        print("\nInterrupted, terminating pool...")
        pool.terminate()
        pool.join()
        save_results(results_dict)
        break
    
    # Prepare next batch of retries
    if failed_jobs:
        jobs = [(id, 0, count) for id, _, count in failed_jobs if count < args.max_retries]
        if jobs:
            print(f"\nRetrying {len(jobs)} failed jobs...")
            failed_jobs = [fj for fj in failed_jobs if fj[2] >= args.max_retries]  # keep permanently failed
    else:
        jobs = []

# Final summary
print("\n" + "=" * 50)
print("FINAL SUMMARY")
print("=" * 50)

successful = sum(1 for v in results_dict.values() if not np.isnan(v))
failed = sum(1 for v in results_dict.values() if np.isnan(v))

print(f"Total nodes: {len(ids)}")
print(f"Successfully computed: {successful}")
print(f"Failed: {failed}")

if failed > 0:
    failed_ids = [id for id, v in results_dict.items() if np.isnan(v)]
    print(f"Failed IDs: {failed_ids}")

# Save final results
save_results(results_dict)
print(f"\nResults saved to {outname}")

# Clean up temp directories
cleanup_temp_dirs()
print("Temporary files cleaned up")