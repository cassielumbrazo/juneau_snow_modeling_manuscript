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

Use [the SNOWPACK profile explorer](notebooks/snowpack_profiles_explorer.ipynb) in the
`juneau_seasonal_snow` environment to select a site, `.pro` simulation, water year,
and variable. [Figure 6](notebooks/figure6_publication.ipynb) plots density and
temperature with the Table 2 pit dates and exports a second version with observed
and simulated profile columns. [Figure 7](notebooks/figure7_publication.ipynb)
plots liquid water content and grain type. Both publication notebooks write PNG and
PDF files to `figures/files/`.

To change the two manuscript pits, edit `selected_dates` in
[the Table 2 pit selector](notebooks/select_table2_snowpit.ipynb) and run it.
Then rerun Figures 5 and 6 and [Table 2](../tables/table2_publication.ipynb)
to refresh their outputs from the shared CSV. The all-pit notebook ranks candidates
without changing the publication selection.
