# Python environments

## Rasterio: Figure 1

`rasterio.yml` is a full export of the installed `rasterio` Conda environment
at `/home/cassie/programs/miniforge3/envs/rasterio`, captured on 2026-10-28.
It includes Python 3.13.1, package versions, build identifiers, and the
`conda-forge` channel. The machine-specific installation prefix was removed.
This is the current environment snapshot, not a verified historical snapshot
from the date the submitted figures were generated.

The export targets **Linux x86_64** and includes the environment's installed
packages and dependencies, rather than only the imports used by Figure 1.
It is not intended as a portable macOS/Windows specification. Recreation also
depends on the recorded package builds remaining available from conda-forge.

### Recreate and select the environment

Install Conda (for example, through Miniforge) first. From the repository root,
in a terminal initialized for Conda, run:

```bash
conda env create --name manuscript-rasterio --file envs/rasterio.yml
conda activate manuscript-rasterio
python -m ipykernel install --user --name manuscript-rasterio --display-name "Manuscript rasterio"
```

The separate environment name preserves any existing `rasterio` environment.
In VS Code, open `figures/figure1.ipynb` and select **Manuscript rasterio** as
the notebook kernel (or select the `manuscript-rasterio` Python environment).
An existing Jupyter frontend can use the registered kernel too; this snapshot
includes `ipykernel`, but does not provide a JupyterLab server.

### Check the installation

With the recreated environment activated:

```bash
python -c "import rasterio, rioxarray, geopandas, cartopy, cfgrib, matplotlib, matplotlib_scalebar, seaborn, pandas, numpy, xarray, scipy, ipykernel; print('Figure 1 imports OK')"
```

These imports were checked successfully in the original installed environment.
A fresh environment has not yet been created or tested from this export.
The check verifies imports, not the complete figure calculation.

Figure 1 still requires its external terrain and other input files. Check the
notebook's original input and figure export paths before running. Cartopy may
also need access to its map-data cache or download missing map datasets.
Recreating the Python environment does not copy these datasets or change paths.

### Refresh the snapshot after intentional environment changes

Export from the environment actually used for the figures:

```bash
conda env export --name manuscript-rasterio > envs/rasterio.yml
```

Remove the final `prefix:` line, update the capture date and provenance above,
and review the changes before committing. Avoid refreshing from a different
environment accidentally. The separate `xarray` environment used by the other
figure/table notebooks is not captured here yet.
