import pandas as pd
import numpy as np
from matplotlib import pyplot as plt
import argparse
from ovito.io import import_file, export_file
from ovito.modifiers import PolyhedralTemplateMatchingModifier as PTM
from ovito.modifiers import GrainSegmentationModifier as GSM
from ovito.modifiers import ExpressionSelectionModifier as select
from ovito.modifiers import DeleteSelectedModifier as delete
from ovito.modifiers import ConstructSurfaceModifier as surface
from ovito.pipeline import Pipeline, StaticSource

parser = argparse.ArgumentParser()
parser.add_argument('-n', "--name", required=True)
parser.add_argument('-N', type=int, required=True)
parser.add_argument('-s', type=str, default='polycrystall.dat', required=False)
args = parser.parse_args()

name = f'workspace/{args.name}/dat/{args.structure}'
pipeline = import_file(name)
data0 = pipeline.compute()
ptm = PTM(output_orientation=True)
pipeline.modifiers.append(ptm)
gsm = GSM(orphan_adoption=False)
pipeline.modifiers.append(gsm)
selection1 = select(expression='Grain==0')
pipeline.modifiers.append(selection1)
pipeline.modifiers.append(delete())
for j in range(args.N):
    pipeline.modifiers.append(surface(radius=2.5, smoothing_level=0, select_surface_particles=True))
    pipeline.modifiers.append(delete())
output = pipeline.compute()  
ids_s = output.particles['Particle Identifier'][:]
ids = data0.particles['Particle Identifier'][:]
inds = np.ones_like(ids)
for j in ids_s:
    ii = np.where(ids==j)
    inds[ii]=2

data0.particles_.create_property('Particle Type', data=inds)
export_file(pipeline, f"workspace/{args.name}/dat/grain_interior.dat", "lammps/data")

pipeline = Pipeline(source = StaticSource(data=data0))
export_file(pipeline, f"workspace/{args.name}/dat/{args.structure.replace('.dat', '')}_fixed.dat", "lammps/data")



