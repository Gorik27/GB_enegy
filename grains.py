import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-n', "--name", required=True)
parser.add_argument('-i', "--input", required=True)
args = parser.parse_args()

df = pd.read_csv(f'workspace/{args.name}/thermo_output/{args.input}.txt')
df = df.sort_values(by='step')

x = df['step']
y = df['atoms_mean']*df['grains']
plt.plot(x, y, 'o')
plt.show()