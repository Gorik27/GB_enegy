import numpy as np
from matplotlib import pyplot as plt
import pandas as pd
import glob, re
import sys
import argparse


def main(args):
    name = args.name
    n = args.n
    inp = args.inp
    file = f"../workspace/{name}/thermo_output/{inp}.txt"
    print(file)
    df = pd.read_csv(file, sep='; ', comment='#', header=0, index_col=None)
    t = df['time']
    pe = df['pe']
    T = df['temp']
    P = df['press']
    N = []
    g_N = []
    g_Nmax = []
    g_Nvar = []
    g_Nmin = []
    step = []

    if args.dump_step:
        import warnings
        warnings.filterwarnings('ignore', message='.*OVITO.*PyPI')
        from ovito.io import import_file, export_file
        from ovito import scene
        from ovito.modifiers import PolyhedralTemplateMatchingModifier as PTM
        from ovito.modifiers import GrainSegmentationModifier as GS


        dumps = sorted(glob.glob(f"../workspace/{name}/dump/{inp}/dump_*.cfg"))

        for j, dump in enumerate(dumps):
            fname = dump.split('/')[-1]
            number = int(re.findall(r'\d+', fname)[-1])
            if j%args.dump_step == 0:
                print(f'dump {j} from {len(dumps)}')
                pipeline = import_file(dump)
                ptm = PTM(
                    output_ordering = True,
                    output_orientation = True
                )
                gs = GS(
                    orphan_adoption = False,
                    min_grain_size = args.min_grain
                )
                pipeline.modifiers.append(ptm)
                pipeline.modifiers.append(gs)
                data = pipeline.compute()
                grains = data.tables['grains']
                #g_id = grains['Grain Identifier']
                gn = np.array(grains['Grain Size'])
                N.append(data.attributes['GrainSegmentation.grain_count'])
                g_N.append(gn.mean())
                g_Nmax.append(gn.max())
                g_Nvar.append(gn.var())
                g_Nmin.append(gn.min())
                step.append(number)
        
    #pipeline.add_to_scene()

    def rolling_mean(numbers_series, window_size):
        windows = numbers_series.rolling(window_size)
        moving_averages = windows.mean()
        moving_averages_list = moving_averages.tolist()
        final_list = moving_averages_list[window_size - 1:]
        return final_list

    pe1 = rolling_mean(pe, n)
    P1 = rolling_mean(P, n)
    t1 = rolling_mean(t, n)
    t = np.array(t)
    t1 = np.array(t1)

    f, ((ax1, ax5), (ax3, ax7)) = plt.subplots(2, 2)
    i0 = args.offset
    ax1.plot(t[i0:], pe[i0:])
    ax2 = ax1.twinx()
    ax2.plot(t[i0:], P[i0:], color='red')
    ax2.hlines(0, xmin=t[i0:].min(), xmax=t[i0:].max(), linestyle='--', color='grey')
    ax1.set_xlabel('$t, ps$')
    ax2.set_xlabel('$t, ps$')
    ax1.set_ylabel('$E_{pot}, eV$')
    ax2.set_ylabel('$P, bar$')

    ax3.plot(t1[i0:], pe1[i0:])
    ax4 = ax3.twinx()
    ax4.plot(t1[i0:], P1[i0:], color='red')
    if args.save:
        x = t1[i0:]
        y1 = np.array(pe1[i0:])
        y2 = np.array(P1[i0:])
        out = np.concatenate((x.reshape((x.shape[0], 1)), 
                            y1.reshape((y1.shape[0], 1)),
                            y2.reshape((y2.shape[0], 1))), axis=1)
        np.savetxt(f'../workspace/{name}/images/plot.{inp}_time{round(t[-1])}.txt', 
                   out, header='t [ps], E_pot [eV], P [bar]')
    ax4.hlines(0, xmin=t1[i0:].min(), xmax=t1[i0:].max(), linestyle='--', color='grey')
    ax3.set_xlabel('$t, ps$')
    ax4.set_xlabel('$t, ps$')
    ax3.set_ylabel('$<E_{pot}>_{roll}, eV$')
    ax4.set_ylabel('$<P>_{roll}, bar$')
    ax3.set_title(f'rolling mean over {n}')
    ax4.set_title(f'rolling mean over {n}')

    if args.dump_step:
        ax5.plot(step, g_N, 'o')
        ax6 = ax5.twinx()
        ax6.plot(step, N, 'o', color='red')
        ax5.set_xlabel('step')
        ax5.set_ylabel('atoms in grain')
        ax6.set_ylabel('grains')

        ax7.plot(step, g_Nvar, 'o')
        ax8 = ax7.twinx()
        ax8.plot(step, N, 'o', color='red')
        ax7.set_xlabel('step')
        ax7.set_ylabel('atoms in max grain')
        ax8.set_ylabel('grains')

        df = pd.DataFrame({
            'step': step,
            'grains': N, 
            'atoms_mean': g_N,
            'atoms_var': g_Nvar,
            'atoms_max': g_Nmax,
            'atoms_min': g_Nmin})

        
        df.to_csv(f'../workspace/{name}/thermo_output/grains_{inp}.txt')

    f.suptitle(f"{inp.replace('_', ' ')} {name} {round(t[-1])}ps")
    f.tight_layout()
    plt.savefig(f'../workspace/{name}/images/plot.{inp}_time{round(t[-1])}_{args.postfix}.png')
    plt.show()



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True, help='for example STGB_210')
    parser.add_argument("-n", required=True, type=int)
    parser.add_argument("--postfix", required=False, default='', help="add this postfix at the end of output file's names")
    parser.add_argument("--offset", required=False, type=int, default=0)
    parser.add_argument("--inp", required=True)
    parser.add_argument("-s", "--save", default=False, action='store_true', required=False,
    help='save data in file') 
    parser.add_argument("--min-grain", dest='min_grain', required=False, default=1000)
    parser.add_argument("--dump-step", dest='dump_step', required=False)
    args = parser.parse_args()
    main(args)
