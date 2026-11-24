"""Read and plot ground-aligned stratigraphy from ASCII SNOWPACK PRO output."""

from dataclasses import dataclass
from datetime import datetime
import mmap
from pathlib import Path

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from matplotlib.ticker import MultipleLocator
import numpy as np
import pandas as pd
import seaborn as sns


@dataclass(frozen=True)
class Variable:
    code: bytes
    title: str
    label: str
    limits: tuple[float, float] | None = None
    ticks: tuple[float, ...] = ()


VARIABLES = {
    'density': Variable(b'0502', 'Snow density', 'snow density (kg m$^{-3}$)',
                        (0, 600), (0, 200, 400, 600)),
    'temperature': Variable(b'0503', 'Snow temperature', 'snow temperature (°C)',
                            (-20, 0), (-20, -15, -10, -5, 0)),
    'liquid_water': Variable(b'0506', 'Liquid water content', 'liquid water content (vol. %)',
                             (0, 4), (0, 1, 2, 3, 4)),
    'grain_type': Variable(b'0513', 'Snow grain type', 'snow grain type'),
}

# Swiss F1F2F3 primary codes, 772 for MFcr, and NiViz-inspired colors.
GRAINS = {
    1: ('PP', '#00ee00'),
    2: ('DF', '#228b22'),
    3: ('RG', '#ffb6c1'),
    4: ('FC', '#add8e6'),
    5: ('DH', '#0000ff'),
    6: ('SH', '#ff00ff'),
    7: ('MF', '#ff0000'),
    10: ('MFcr', '#ff0000'),
    8: ('IF', '#00ffff'),
    9: ('FCxr', '#76b9d0'),
}


GRAIN_NAMES = {
    1: 'Precipitation particles',
    2: 'Decomposing and fragmented particles',
    3: 'Rounded grains',
    4: 'Faceted crystals',
    5: 'Depth hoar',
    6: 'Surface hoar',
    7: 'Melt forms',
    10: 'Melt–freeze crust',
    8: 'Ice formations',
    9: 'Rounding faceted particles',
}


def _draw_grain_legend(fig, ax):
    handles = [
        Patch(facecolor=color, edgecolor='black' if code == 10 else '#45515a',
              linewidth=0.6, hatch='||||' if code == 10 else None,
              label=f'{abbreviation}  {GRAIN_NAMES[code]}')
        for code, (abbreviation, color) in GRAINS.items()
    ]
    panel = ax.get_position()
    center = (panel.x0 + panel.x1) / 2
    fig.legend(handles=handles, title='Snow grain types', title_fontsize=11,
               loc='upper center', bbox_to_anchor=(center, 0.22), borderaxespad=0,
               ncols=3, fontsize=9, frameon=True, facecolor='white', edgecolor='#8e99a4',
               framealpha=1, fancybox=False, borderpad=0.9, handlelength=2, labelspacing=0.8)


@dataclass
class Profile:
    time: datetime
    bottom_cm: np.ndarray
    top_cm: np.ndarray
    values: dict[str, np.ndarray]


def water_year_window(year):
    """Return inclusive start and exclusive stop for a water year ending in September."""
    return pd.Timestamp(year - 1, 10, 1), pd.Timestamp(year, 10, 1)


def read_pit_selection(path, window):
    """Load both publication pit timestamps and check their plot coverage."""
    selection = pd.read_csv(path, parse_dates=['date', 'model_time'])
    if (len(selection) != 2 or not selection['date'].is_unique
            or not selection['model_time'].between(*window, inclusive='left').all()):
        raise ValueError('Expected two distinct Table 2 pit dates within the figure window.')
    return selection


def _values(count, payload):
    values = np.fromstring(payload.decode('ascii'), sep=',')
    if len(values) != int(count):
        raise ValueError(f'Declared {int(count)} values, read {len(values)}.')
    return values


def _snow_profile(time, fields, variables):
    heights = fields[b'0501']
    if np.any(~np.isfinite(heights)) or np.any(heights <= -999):
        raise ValueError('Invalid layer heights.')
    tops = heights[heights > 0]
    if not len(tops):
        return Profile(time, tops, tops, {})
    if np.any(np.diff(heights) < 0):
        raise ValueError('Layer heights must be ordered from bottom to top.')
    # With soil, 0501 starts with the bottom soil boundary. Without soil,
    # every positive entry is a layer top and the first layer starts at zero.
    bottoms = np.r_[0, tops[:-1]]
    nonzero = tops > bottoms  # Very thin layers can round to equal heights in PRO.
    values = {}
    for name in variables:
        variable = VARIABLES[name]
        layer_values = fields[variable.code]
        if name == 'grain_type' and len(layer_values) == len(tops) + 1:
            # 0513 can append a surface-hoar marker that has no layer thickness.
            layer_values = layer_values[:-1]
        expected = {len(tops)}
        if heights[0] <= 0 and name != 'grain_type':
            expected.add(len(heights) - 1)
        if len(layer_values) not in expected:
            raise ValueError(f'Cannot align {name} ({len(layer_values)} values) '
                             f'with {len(tops)} snow layers.')
        layer_values = layer_values[-len(tops):][nonzero]
        values[name] = np.where((layer_values <= -999) | ~np.isfinite(layer_values),
                                np.nan, layer_values)
    return Profile(time, bottoms[nonzero], tops[nonzero], values)


def read_profiles(path, start, stop, variables=tuple(VARIABLES), *, sample_hours=1):
    """Read selected fields between start (inclusive) and stop (exclusive).

    Thin regular output by keeping the first profile per sample_hours interval.
    The second return value is the median native output interval in days.
    """
    path = Path(path)
    start, stop = pd.Timestamp(start), pd.Timestamp(stop)
    if stop <= start or sample_hours <= 0:
        raise ValueError('Choose an increasing time window and positive sample_hours.')
    variables = tuple(variables)
    codes = {b'0501', *(VARIABLES[name].code for name in variables)}
    times, profiles = [], []
    last_bin = None
    with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as data:
        position = data.find(b'[DATA]')
        if position < 0:
            raise ValueError(f'{path.name}: missing [DATA] section.')
        position = data.find(b'\n0500,', position)
        while position >= 0:
            data.seek(position + 1)
            time = datetime.strptime(data.readline()[5:].strip().decode('ascii'),
                                     '%d.%m.%Y %H:%M:%S')
            block_start = data.tell()
            if time >= stop:
                break
            following = data.find(b'\n0500,', block_start - 1)
            if time >= start:
                if times and time <= times[-1]:
                    raise ValueError(f'{path.name}: profiles are out of order at {time}.')
                times.append(time)
                sample_bin = (time - start).total_seconds() // (sample_hours * 3600)
                if sample_bin != last_bin:
                    fields = {}
                    try:
                        block_end = len(data) if following < 0 else following
                        for line in data[block_start:block_end].splitlines():
                            if line[:4] in codes:
                                key, count, payload = line.split(b',', 2)
                                fields[key] = _values(count, payload)
                        profiles.append(_snow_profile(time, fields, variables))
                    except (KeyError, ValueError) as error:
                        raise ValueError(f'{path.name} at {time}: {error}') from error
                    last_bin = sample_bin
            position = following
    if not profiles:
        raise ValueError(f'{path.name}: no profiles between {start} and {stop}.')
    cadence = float(np.median(np.diff(mdates.date2num(times)))) if len(times) > 1 else 1 / 24
    return profiles, max(cadence, sample_hours / 24)


def _layer_rectangles(profiles, variable, cadence):
    times = mdates.date2num([profile.time for profile in profiles])
    # Each profile is centered on its timestamp. Leave larger reporting gaps blank.
    half_gaps = np.minimum(np.diff(times) / 2, cadence * 0.55)
    left = times - np.r_[cadence / 2, half_gaps]
    right = times + np.r_[half_gaps, cadence / 2]
    counts = np.array([len(profile.top_cm) for profile in profiles])
    lo = np.repeat(left, counts)
    hi = np.repeat(right, counts)
    bottom = np.concatenate([profile.bottom_cm for profile in profiles])
    top = np.concatenate([profile.top_cm for profile in profiles])
    values = np.concatenate([p.values[variable] for p in profiles if len(p.top_cm)]) if len(top) else np.empty(0)
    corners = np.stack([np.column_stack(pair) for pair in
                        ((lo, bottom), (hi, bottom), (hi, top), (lo, top))], axis=1)
    return corners, values


def _continuous_scale(variable, limits):
    style = VARIABLES[variable]
    palette = {
        'density': [(0, '#eeeeee'), (1/3, '#00ffff'), (2/3, '#0000ff'), (1, '#000080')],
        'temperature': [(0, '#000080'), (0.25, '#0000ff'), (0.5, '#00ffff'),
                        (0.75, '#eeeeee'), (1, '#ff0000')],
        'liquid_water': [(0, '#eeeeee'), (0.25, '#00ffff'), (0.65, '#0000ff'), (1, '#000080')],
    }
    cmap = mpl.colors.LinearSegmentedColormap.from_list(variable, palette[variable])
    norm = mpl.colors.Normalize(*(limits or style.limits), clip=True)
    ticks = style.ticks if limits is None else None
    return cmap, norm, ticks


def _draw_layers(ax, cax, profiles, variable, cadence, limits):
    corners, values = _layer_rectangles(profiles, variable, cadence)
    style = VARIABLES[variable]
    valid = np.isfinite(values)
    if variable == 'grain_type':
        swiss = np.where(valid, values, 0).astype(int)
        primary = np.where(swiss == 772, 10, swiss // 100)
        classes = list(GRAINS)
        indices = np.full(len(values), np.nan)
        for index, code in enumerate(classes):
            indices[primary == code] = index
        valid &= np.isfinite(indices)
        values = indices
        cmap = mpl.colors.ListedColormap([GRAINS[key][1] for key in classes])
        norm = mpl.colors.BoundaryNorm(np.arange(len(classes) + 1) - 0.5, cmap.N)
        ticks = np.arange(len(classes))
    else:
        cmap, norm, ticks = _continuous_scale(variable, limits)
    collection = PolyCollection(corners[valid], cmap=cmap, norm=norm, edgecolors='none',
                                antialiaseds=False, rasterized=True, zorder=2)
    collection.set_array(values[valid])
    ax.add_collection(collection, autolim=False)
    colorbar = ax.figure.colorbar(collection, cax=cax, ticks=ticks, ticklocation='left')
    colorbar.set_label(style.label)
    colorbar.ax.tick_params(labelsize=9)
    if variable == 'grain_type':
        crust = primary == 10
        # Apply the same vertical stripe to the layers and the legend swatch.
        ax.add_collection(PolyCollection(corners[crust], facecolors='none', edgecolors='black',
                                         linewidths=0, hatch='||||', rasterized=True, zorder=2.1),
                          autolim=False)
        index = classes.index(10)
        cax.add_patch(Rectangle((0, index - 0.5), 1, 1, facecolor='none', edgecolor='black',
                                linewidth=0, hatch='||||'))
        colorbar.set_ticks(ticks, labels=[GRAINS[key][0] for key in classes])
        cax.invert_yaxis()


def plot_profiles(profiles, cadence, variables, window, *, heading, subtitle,
                  depth_max=None, color_limits=None, pit_times=(), pit_comparisons=(),
                  monthly_date_ticks=False, pit_line_color='black', timeline_hspace=0.34,
                  grain_legend=False):
    """Draw a single timeline or stacked manuscript panels."""
    peak = max((p.top_cm[-1] for p in profiles if len(p.top_cm)), default=0)
    depth_max = depth_max or max(50, np.ceil(peak / 50) * 50)
    color_limits = color_limits or {}
    pit_times = tuple(pit_times)
    with sns.axes_style('darkgrid'), mpl.rc_context({
        'font.family': 'DejaVu Sans', 'pdf.fonttype': 42, 'hatch.linewidth': 0.6,
    }):
        include_profiles = bool(pit_comparisons)
        height = 11 if include_profiles else (7.8 if len(variables) > 1 else 4.5)
        fig = plt.figure(figsize=(12, height + (2.4 if grain_legend else 0)))
        timeline_bottom = 0.415 if include_profiles else 0.10
        if grain_legend:
            timeline_bottom = 0.29
        grid = fig.add_gridspec(len(variables), 2, left=0.12, right=0.92,
                               bottom=timeline_bottom,
                               top=0.88 if include_profiles else (0.82 if len(variables) > 1 else 0.72),
                               width_ratios=(0.022, 1), wspace=0.08, hspace=timeline_hspace)
        fig.text(0.12, 0.97, heading, va='top', fontsize=16, weight='bold')
        subtitle_y = 0.938 if include_profiles else (0.925 if len(variables) > 1 else 0.885)
        fig.text(0.12, subtitle_y, subtitle, va='top', fontsize=10, color='#45515a')
        date_axis = None
        for index, variable in enumerate(variables):
            cax = fig.add_subplot(grid[index, 0])
            ax = fig.add_subplot(grid[index, 1], sharex=date_axis)
            if monthly_date_ticks and index == 0:
                date_axis = ax
            _draw_layers(ax, cax, profiles, variable, cadence, color_limits.get(variable))
            ax.set_xlim(*mdates.date2num(window))
            ax.set_ylim(0, depth_max)
            ax.yaxis.tick_right()
            ax.yaxis.set_label_position('right')
            ax.set_ylabel('snow depth (cm)')
            ax.yaxis.set_major_locator(MultipleLocator(50))
            locator = mdates.AutoDateLocator(minticks=5, maxticks=11)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            ax.xaxis.set_minor_locator(mdates.WeekdayLocator())
            ax.tick_params(labelsize=9)
            if monthly_date_ticks:
                ax.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=1))
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%-d %b\n%Y'))
                ax.xaxis.set_minor_locator(mdates.MonthLocator(bymonthday=1))
                ax.tick_params(axis='x', which='major', bottom=True,
                               labelbottom=index == len(variables) - 1,
                               length=5, width=0.8, color='#46515b')
            ax.grid(which='minor', axis='x', alpha=0.5, linestyle=':')
            ax.set_title(f'Simulated {VARIABLES[variable].title.lower()}', loc='left', fontsize=12)
            if len(variables) > 1:
                ax.text(0.009, 0.96, f'{chr(65 + index)})', transform=ax.transAxes,
                        va='top', fontsize=10, color='dimgrey', zorder=4,
                        bbox=dict(facecolor=ax.get_facecolor(), edgecolor='none', pad=1))
            for time in pit_times:
                ax.axvline(time, color=pit_line_color, linestyle='--', linewidth=1.3, zorder=3)
            if pit_times and index == 0:
                pit_reference = 'panels C–F' if include_profiles else 'Table 2'
                handle = Line2D([], [], color=pit_line_color, linestyle='--', linewidth=1.3,
                                label=f'Snow pit observations ({pit_reference})')
                ax.legend(handles=[handle], loc='upper right', fontsize=9, framealpha=1)
        if include_profiles:
            _draw_pit_comparisons(fig, pit_comparisons, variables, color_limits, depth_max)
        if grain_legend:
            _draw_grain_legend(fig, ax)
    return fig


def _profile_bands(ax, left, right, bottom, top, values, cmap, norm):
    left = np.broadcast_to(left, len(bottom))
    right = np.broadcast_to(right, len(bottom))
    vertices = np.stack([np.column_stack(pair) for pair in
                         ((left, bottom), (right, bottom), (right, top), (left, top))], axis=1)
    ax.add_collection(PolyCollection(vertices, array=np.ma.asarray(values), cmap=cmap, norm=norm,
                                     edgecolors='none', antialiaseds=False, zorder=2))


def _observed_density_bands(ax, rows, cmap, norm):
    density = rows.loc[rows['measurement'].eq('density')].dropna(
        subset=['bottom_height_cm', 'top_height_cm', 'density_kg_m3'])
    edges = np.unique(density[['bottom_height_cm', 'top_height_cm']].to_numpy())
    bands = []
    for bottom, top in zip(edges[:-1], edges[1:]):
        values = density.loc[(density['bottom_height_cm'] <= bottom) &
                             (density['top_height_cm'] >= top), 'density_kg_m3']
        slots = np.linspace(-0.30, 0.30, len(values) + 1)
        bands.extend((left, right, bottom, top, value)
                     for left, right, value in zip(slots[:-1], slots[1:], values))
    if not bands:
        raise ValueError('Expected observed density intervals for each pit.')
    _profile_bands(ax, *np.asarray(bands).T, cmap, norm)


def _observed_temperature_bands(ax, rows, cmap, norm):
    points = rows.loc[rows['temperature_location'].isin(['snow', 'surface'])].dropna(
        subset=['temperature_height_cm', 'temperature_c'])
    points = points.groupby('temperature_height_cm')['temperature_c'].mean()
    if len(points) < 2:
        raise ValueError('Expected distinct observed temperature heights for each pit.')
    edges = np.linspace(points.index[0], points.index[-1], 321)
    values = np.interp((edges[:-1] + edges[1:]) / 2, points.index, points)
    _profile_bands(ax, -0.30, 0.30, edges[:-1], edges[1:], values, cmap, norm)
    ax.scatter(np.full(len(points), 0.36), points.index, s=8, color='#344453', zorder=4)


def _draw_pit_comparisons(fig, comparisons, variables, color_limits, depth_max):
    """Plot ground-aligned observed and modeled columns with the timeline scales."""
    grid = fig.add_gridspec(1, len(comparisons), left=0.142, right=0.92,
                           bottom=0.10, top=0.282, wspace=0.30)
    index = 0
    for pit_index, (pit_label, date, field_rows, model) in enumerate(comparisons):
        obs_depth = field_rows['snow_depth_cm'].max()
        model_depth = model.top_cm[-1]
        pair = grid[pit_index].subgridspec(1, len(variables), wspace=0.22)
        for var_index, variable in enumerate(variables):
            ax = fig.add_subplot(pair[var_index])
            if var_index == 0:
                fig.text(ax.get_position().x0, 0.333, f'{pit_label} · {date:%-d %b %Y}',
                         fontsize=11, weight='bold', va='bottom')
            cmap, norm, _ = _continuous_scale(variable, color_limits.get(variable))
            if variable == 'density':
                _observed_density_bands(ax, field_rows, cmap, norm)
            else:
                _observed_temperature_bands(ax, field_rows, cmap, norm)
            _profile_bands(ax, 0.70, 1.30, model.bottom_cm, model.top_cm,
                           np.ma.masked_invalid(model.values[variable]), cmap, norm)
            for x, depth in ((0, obs_depth), (1, model_depth)):
                ax.add_patch(Rectangle((x - 0.30, 0), 0.60, depth, fill=False,
                                       edgecolor='#344453', linewidth=0.6, zorder=3))
            ax.set_title(f'{chr(67 + index)}) {VARIABLES[variable].title}',
                         loc='left', fontsize=11, pad=7)
            ax.set(xlim=(-0.46, 1.46), ylim=(0, depth_max),
                   xticks=[0, 1], xticklabels=['Observed', 'Simulated'])
            ax.yaxis.set_major_locator(MultipleLocator(50))
            ax.tick_params(axis='both', labelsize=9, length=0)
            ax.grid(axis='x', visible=False)
            ax.tick_params(axis='y', labelleft=index == 0)
            if index == 0:
                ax.set_ylabel('Height above ground (cm)', fontsize=9)
            index += 1
    fig.text(0.142, 0.040,
             'Dots mark observed temperature readings. Color between readings is interpolated.',
             fontsize=8, color='#45515a')


def save_figure(fig, output_dir, stem):
    """Save the manuscript's PNG and PDF formats at 300 dpi."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for extension in ('png', 'pdf'):
        fig.savefig(output_dir / f'{stem}.{extension}', dpi=300, facecolor='white')
