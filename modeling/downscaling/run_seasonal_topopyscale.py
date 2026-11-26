"""Replay the existing soil baseline through WY2020, then test WY2021 forcing."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import subprocess

import numpy as np
import pandas as pd
import xarray as xr

HERE = Path(__file__).resolve().parent
MODEL = Path('/home/cassie/python/models/run_snowpack/sites')
GRID = Path('/home/cassie/python/models/run_topopyscale/icefield_domain/WY2021')
SITES = ('ppsa', 'tram', 'heen')
RESOLUTIONS = (1000, 500)
PERIOD = 'WY2020-WY2025'
START = pd.Timestamp('2019-10-01T06:00')
YEAR = pd.date_range('2020-10-01', periods=8760, freq='h')
HOURS = pd.date_range(START, YEAR[-1], freq='h')
FIELDS = ('TA', 'RH', 'VW', 'DW', 'ISWR', 'ILWR', 'PSUM', 'PS')


def read_smet(path, columns=None):
    header = {}
    with path.open() as stream:
        for line in stream:
            if line.strip() == '[DATA]':
                break
            if '=' in line:
                key, value = line.split('=', 1)
                header[key.strip()] = value.strip()
        else:
            raise ValueError(f'Missing SMET data section in {path}')
        data = pd.read_csv(stream, sep=r'\s+', names=header['fields'].split(),
                           usecols=columns, index_col='timestamp', parse_dates=['timestamp'])
    data.index -= pd.Timedelta(hours=float(header['tz']))
    if not data.index.is_unique or not data.index.is_monotonic_increasing:
        raise ValueError(f'Invalid timestamps in {path}')
    return header, data.replace(float(header['nodata']), np.nan)


def locations(site, resolution):
    base_id = f'hrrrak_lapserate_{site}_{PERIOD}'
    parent = MODEL / site
    base = parent / 'input' / f'hrrrak_lapserate_{PERIOD}' / base_id
    test_id = f'topopyscale_{resolution}m_{site}_WY2021'
    test = parent / 'input' / f'topopyscale_{resolution}m_WY2021' / test_id
    return parent, base, test


def extract(site, resolution, header):
    grid = GRID / f'{resolution}m'
    x, y = (float(header[k]) for k in ('easting', 'northing'))
    with xr.open_dataset(grid / 'terrain.nc') as terrain:
        selected = terrain.sel(x=x, y=y, method='nearest')
        cell = int(selected.cell_id)
        if (cell < 0 or abs(float(selected.x) - x) > resolution / 2
                or abs(float(selected.y) - y) > resolution / 2):
            raise ValueError(f'{site} falls outside the valid {resolution} m grid')
        elevation = float(selected.elevation)
    path = grid / 'forcing.nc'
    with xr.open_dataset(path) as source:
        met = source.isel(cell=cell).load()
    if not met.indexes['time'].equals(YEAR):
        raise ValueError(f'Incomplete WY2021 at {site} ({resolution} m)')
    u, v = met.u.values, met.v.values
    frame = pd.DataFrame(dict(TA=met.t.values, RH=met.rh.values/100, VW=np.hypot(u, v),
                              DW=np.rad2deg(np.arctan2(-u, -v)) % 360, ISWR=met.SW.values,
                              ILWR=met.LW.values, PSUM=met.tp.values, PS=met.p.values), index=YEAR)
    if (not np.isfinite(frame.to_numpy()).all() or not frame.RH.between(0, 1).all()
            or (frame[['ISWR', 'ILWR', 'PSUM', 'PS']] < 0).any().any()):
        raise ValueError(f'Invalid forcing at {site} ({resolution} m)')
    site_elevation = float(header['altitude'])
    summary = dict(site=site, resolution_m=resolution, cell=cell,
                   site_elevation_m=site_elevation, grid_elevation_m=elevation,
                   cell_minus_site_m=elevation-site_elevation, forcing=str(path),
                   profile_fallback_hours=int(met.profile_fallback.sum()),
                   temperature_lapse_adjustment_K=0, threshold_C=1.2)
    return frame, summary


def prepare(site, resolution):
    parent, base, test = locations(site, resolution)
    config = parent / 'config' / f'{test.name}.ini'
    log = parent / 'logs' / f'{test.name}.log'
    output = parent / 'output' / f'{test.name}_soil.smet'
    if any(p.exists() for p in (test.parent, config, log, output)):
        raise FileExistsError(f'Existing experiment {test.name}')
    header, old = read_smet(base.with_suffix('.smet'))
    # The inherited soil profile starts at 06 UTC. Keep the preceding input hour.
    spinup = old.loc['2019-10-01T05:00':'2020-09-30T23:00', list(FIELDS)]
    hours = pd.date_range('2019-10-01T05:00', '2020-09-30T23:00', freq='h')
    if not spinup.index.equals(hours) or not np.isfinite(spinup.to_numpy()).all():
        raise ValueError(f'Incomplete spin-up at {site}')
    frame, meta = extract(site, resolution, header)
    changes = dict(station_id=test.name, station_name=f'{site.upper()} TopoPyScale {resolution} m',
                   source='HRRR-AK lapse-rate spin-up through WY2020; TopoPyScale in WY2021')
    for key in ('lapse_rate', 'hrrr_elevation', 'ta_correction'):
        header.pop(key, None)
    header.update(changes)
    test.parent.mkdir()
    with test.with_suffix('.smet').open('x') as out:
        out.write('SMET 1.1 ASCII\n[HEADER]\n')
        for k, v in header.items():
            out.write(f'{k:20} = {v}\n')
        out.write('[DATA]\n')
        pd.concat([spinup, frame]).to_csv(out, sep=' ', header=False,
                    date_format='%Y-%m-%dT%H:%M', float_format='%.6f')
    sno = base.with_name(base.name + '_soil.sno').read_text()
    for key, value in changes.items():
        sno = re.sub(rf'(?m)^{key}\s*=.*$', f'{key:20} = {value}', sno)
    sno = re.sub(r'(?m)^(lapse_rate|hrrr_elevation|ta_correction)\s*=.*\n', '', sno)
    test.with_name(test.name + '_soil.sno').write_text(sno)
    original = parent / 'config' / f'hrrrak_lapserate_soil_{site}_{PERIOD}.ini'
    settings = original.read_text()
    if not re.search(r'(?m)^SNP_SOIL\s*=\s*true\b', settings) or not re.search(
            r'(?m)^PSUM_PH::PRECSPLITTING::snow\s*=\s*274\.35\b', settings):
        raise ValueError(f'Unexpected soil setup or phase threshold in {original}')
    config.write_text(settings.replace(base.name, test.name).replace(
        f'../input/{base.parent.name}', f'../input/{test.parent.name}'))
    meta.update(reference_config=str(original), spinup_hours=len(spinup))
    test.with_suffix('.json').write_text(json.dumps(meta, indent=2)+'\n')
    print(f'{test.name}: {meta["grid_elevation_m"]:.1f} m grid, {meta["site_elevation_m"]:.1f} m site',
          flush=True)


def model_output(path):
    header, data = read_smet(path, ['timestamp', 'HS_mod', 'SWE'])
    units = dict(zip(header['fields'].split(), map(float, header['units_multiplier'].split())))
    return data.assign(depth_m=data.HS_mod * units['HS_mod'], swe_mm=data.SWE * units['SWE'])


def run_case(site, resolution):
    parent, base, test = locations(site, resolution)
    (parent / 'logs').mkdir(exist_ok=True)
    log = parent / 'logs' / f'{test.name}.log'
    command = ['snowpack', '-c', f'{test.name}.ini', '-e', YEAR[-1].isoformat(timespec='minutes')]
    with log.open('x') as out:
        subprocess.run(command, cwd=parent / 'config', stdout=out, stderr=subprocess.STDOUT, check=True)
    if 'FINISHED running' not in log.read_text():
        raise RuntimeError(f'Incomplete simulation. See {log}')
    data = model_output(parent / 'output' / f'{test.name}_soil.smet')
    if not data.index.equals(HOURS) or not np.isfinite(data.to_numpy()).all():
        raise ValueError(f'Incomplete output for {test.name}')
    reference = model_output(parent / 'output' / f'{base.name}_soil.smet')
    pd.testing.assert_frame_equal(data.loc[:'2020-09-30T23:00'],
                                  reference.loc[:'2020-09-30T23:00'])
    print(f'{test.name}: identical spin-up plus 8,760 verified WY2021 hours', flush=True)


if __name__ == '__main__':
    jobs = [(site, res) for site in SITES for res in RESOLUTIONS]
    for job in jobs:
        prepare(*job)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for future in [pool.submit(run_case, *job) for job in jobs]:
            future.result()
