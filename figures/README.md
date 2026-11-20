# Figures

- `notebooks/`: Figure notebooks. Run from the repository root, `figures/`, or `figures/notebooks/`.
- `files/`: Final exported PNG/PDF figures. Existing exports were moved here.

`figure1_basemap.ipynb` creates the standalone satellite map and the paired A/B comparison.
Its `panel_gap` setting controls the separation in inches without changing either map scale.
Only B has the enlarged Alaska inset. The notebook ends with guidance on selecting alternate
imagery using Esri World Imagery Wayback and interpreting mosaic release vs acquisition dates.

Use the rasterio environment for Figures 1 and 3 (Figure 3 uses rioxarray for CRS metadata),
and the xarray environment for Figures 4 and 5. All seven notebooks were run successfully
on 2026-11-11. See [path_check.md](path_check.md) for the path and export check.

Figure 5 and the presentation notebook now write PNG/PDF exports. Figure 5 variants use
distinct filenames, and presentation reveals retain their fixed canvas dimensions.
