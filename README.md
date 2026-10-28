# Juneau snow modeling manuscript

Analysis notebooks for the manuscript on physically based snow modeling in
Southeast Alaska. This repository contains copies of the final figure,
table, and forcing preparation notebooks and selected SNOWPACK run files accompanying the submitted manuscript,
organized for reference during review.

The original files, broader analyses, and development workflows are available in
the [snow_modeling_point repository](https://github.com/cassielumbrazo/snow_modeling_point).

- `figures/`: Figure 1, 3, 4, and 5 notebooks, including the `figure5_bothSWE.ipynb` variant.
- `tables/`: Table 1 and 2 notebooks, including the `table2_lapserate.ipynb` variant.
- `forcing/`: Six SNOWPACK forcing preparation notebooks, two per site. Filenames
  identify the forcing configuration, site, and water years (WY).
- `modeling/`: Configurations (`.ini`), prepared forcing (`.smet`), and initial
  states (`.sno`) for those six runs, copied from `run_snowpack`. See the
  [modeling notes](modeling/README.md) for provenance, path issues, and remaining
  reproducibility requirements. Model outputs are excluded and ignored by Git.

| Site | `hrrrak_lapserate` | `met_hrrrak_lapserate` |
| --- | --- | --- |
| HEEN | WY2020–WY2025 | WY2020–WY2022 |
| PPSA | WY2020–WY2025 | WY2020–WY2025 |
| TRAM | WY2020–WY2025 | WY2023–WY2025 |

Figure and table notebooks were copied from `snow_modeling_point/sites/`, with
the `4_` filename prefix removed. Forcing notebooks were copied from its `heen/`,
`ppsa/`, and `tram/` subfolders, with the `2_` prefix removed. The six forcing
notebooks' SMET output names match the lapse-rate simulation names and water
years referenced in the figure and table analyses (model outputs add `_base`).
Notebook code and saved outputs are preserved.

To rerun a figure or table analysis, use the Python environment noted at the top of its notebook
(`rasterio` for Figure 1; `xarray` for the others). The notebooks still reference
external observations, forcing data, and SNOWPACK output through their original
local paths. Check input and export paths before running; some figure exports
still write to `snow_modeling_point/figures/`. External observations and model
outputs have not been copied into this repository; prepared forcing inputs for
the six selected runs are included in `modeling/`.
Forcing notebooks also retain their original input and SMET export paths;
check these paths and the notebook's environment requirements before rerunning.
