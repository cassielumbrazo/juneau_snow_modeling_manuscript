# Figure path and export check

Checked and rerun on 2026-11-11. All seven notebooks completed from `figures/scripts/`.

Every existing absolute local input path was checked for existence. These inputs remain in
the shared `/hdd/snow_hydrology/` archive or the original SNOWPACK model-output folders;
they were not copied into the manuscript repository. All figure exports use `FIGURE_FILES`
(or its alias `OUTPUT_DIR`), resolved to this repository’s `figures/files/`.

| Notebook | Environment | Referenced local inputs | Execution |
| --- | --- | ---: | --- |
| figure1.ipynb | rasterio | 3 | Passed |
| figure1_basemap.ipynb | rasterio | 3 | Passed |
| figure3.ipynb | rasterio | 15 | Passed |
| figure4.ipynb | xarray | 16 | Passed |
| figure4_presentations.ipynb | xarray | 16 | Passed |
| figure5.ipynb | xarray | 6 | Passed |
| figure5_bothSWE.ipynb | xarray | 16 | Passed |

Export notes:

- Figure 3 required an explicit `import rioxarray` to register the `.rio` accessor; the installed rasterio environment supplies it.
- Figure 5 now saves PNG and PDF; its existing plotted data and analysis were retained.
- Presentation reveals export four fixed-canvas PNG/PDF pairs.
- Figure 5 variants have distinct names so they do not overwrite the primary Figure 5.
- The basemap comparison retains matched map scales and the 0.35-inch frame gap, with a single inset shifted left/down and lowered panel titles.

Output inventory: 19 PNG and 19 PDF files.
