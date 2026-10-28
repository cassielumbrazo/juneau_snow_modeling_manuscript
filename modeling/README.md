# Manuscript SNOWPACK runs

Copied from `/home/cassie/python/models/run_snowpack` for the six lapse-rate
simulations identified by the notebooks in `../forcing/`. Each simulation has
an `.ini` configuration, an `.smet` meteorological forcing file, and an `.sno`
initial-state file. Original filenames, contents, and `sites/<site>/config/`
and `sites/<site>/input/<configuration>_<years>/` structure are preserved.
No files from the model output directories are included.

`simulations.csv` lists the six configurations and their actual forcing time
coverage (UTC). Forcing coverage does not establish the simulation end date.
`manifest.csv` records the original absolute path, size, and SHA-256 checksum
of every copied file. The source repository HEAD at copying was
`a75deda3af47371a422cf76b32b9e98a5e0e93e7`; the source working tree contained
uncommitted files, so the manifest describes the copied snapshot more precisely
than that commit alone.

## Paths and rerunning

Paths inside all copied files are unchanged. The configurations use
`[Input] METEOPATH = ../input/<configuration>_<years>` and
`[Output] METEOPATH = ../output`. The sibling folder structure is preserved,
but path resolution and the working directory must be checked before running.
Create each site's `output/` directory locally when needed; generated files in
these directories are ignored by Git.

`source_run_notes.txt` is an unchanged copy of the original `run_snowpack.txt`.
It documents the command form `snowpack -c <configuration.ini> -e <enddate>`
and some historical run dates. It is not a verified command list for these six
simulations: the HEEN notes question the end date, and the exact end dates used
for all six final runs still need confirmation. No model runs were executed
while preparing this archive. The SNOWPACK/MeteoIO version and build settings
also remain to be recorded for reproducibility.

## Remaining external dependencies

- Install the SNOWPACK executable and its dependencies separately.
- The forcing notebooks retain absolute input and export paths into the original
  repositories and data storage. The prepared `.smet` inputs are included here,
  but regenerating them still requires those external source datasets.
- Figure and table notebooks still read model outputs from
  `/home/cassie/python/models/run_snowpack/sites/<site>/output/`, rather than
  this archive. They also reference external observations and other data.
- Some analysis notebooks reference non-lapse-rate simulations as well. This
  archive includes only the six lapse-rate runs selected for the manuscript;
  running every existing notebook cell may require those additional runs.

This collects the selected run inputs in one place; the full analysis is not yet
self-contained until the remaining paths, datasets, run dates, and software
environment are documented or updated.
