"""Extract measured PPSA density intervals and temperature points from the field workbook."""

import argparse
import csv
from datetime import datetime
from pathlib import Path
import re
from xml.etree import ElementTree
from zipfile import ZipFile


WORKBOOK = Path('/hdd/snow_hydrology/field_data/UAS_Snow_Pit_Field_Data_Summary_WY2025.xlsx')
OUTPUT = Path(__file__).resolve().parents[1] / 'data/ppsa_snowpit_profiles_WY2025.csv'
COLUMNS = (
    'date', 'source_sheet', 'source_row', 'snow_depth_cm', 'measurement',
    'top_height_cm', 'bottom_height_cm', 'density_kg_m3', 'cutter_mass_g',
    'extra_cutter_mass_g', 'temperature_location', 'temperature_height_cm', 'temperature_c',
)


def workbook_rows(path):
    # Read workbook cell values, including the cached post-processed density results.
    with ZipFile(path) as archive:
        def parse(member):
            return ElementTree.fromstring(archive.read(member))

        strings = [
            ''.join(node.text or '' for node in item.findall('.//{*}t'))
            for item in parse('xl/sharedStrings.xml')
        ]
        targets = {
            link.get('Id'): link.get('Target') for link in parse('xl/_rels/workbook.xml.rels')
        }
        for sheet in parse('xl/workbook.xml').findall('.//{*}sheet'):
            name = sheet.get('name')
            if not name.startswith('FieldDay'):
                continue
            relation_id = next(value for key, value in sheet.attrib.items() if key.endswith('}id'))
            target = targets[relation_id]
            member = target.lstrip('/') if target.startswith('/') else f'xl/{target}'
            rows = {}
            for row in parse(member).findall('.//{*}sheetData/{*}row'):
                values = {}
                for cell in row.findall('{*}c'):
                    value = cell.findtext('{*}v')
                    if value is not None:
                        column = re.match(r'[A-Z]+', cell.get('r')).group()
                        values[column] = strings[int(value)] if cell.get('t') == 's' else value
                if values:
                    rows[int(row.get('r'))] = values
            yield name, rows


def number(value):
    if value is None or not value.strip() or value.strip() in {'-', '—'}:
        return None
    return float(value)


def extract(path):
    records = []
    for sheet, rows in workbook_rows(path):
        day = sheet.split('_', 1)[1].replace('April', 'Apr')
        date = datetime.strptime(day, '%d%b%Y').date().isoformat()
        depth = float(rows[8]['D'].strip().lower().removesuffix('cm').strip())
        if not (rows[14]['A'].startswith('Snow Density') and rows[14]['I'] == 'Temperature'):
            raise ValueError(f'Unexpected measurement headers in {sheet}')

        for row, values in rows.items():
            if row < 17:
                continue
            metadata = dict(date=date, source_sheet=sheet, source_row=row, snow_depth_cm=depth)
            if values.get('D') and values.get('F'):
                # Rows with cached zero formulas and no cutter measurement are blank.
                density = number(values['F'])
                top, bottom = number(values.get('A')), number(values.get('C'))
                if top is None or bottom is None or not (0 <= bottom < top <= depth and density > 0):
                    raise ValueError(f'Invalid density interval in {sheet} row {row}')
                records.append(dict(metadata, measurement='density', top_height_cm=top,
                                    bottom_height_cm=bottom, density_kg_m3=density,
                                    cutter_mass_g=number(values['D']),
                                    extra_cutter_mass_g=number(values.get('E'))))

            location = values.get('I', '').strip().lower()
            if not location or not values.get('J'):
                continue
            temperature = number(values['J'])
            if temperature is None:
                continue
            if location == 'air':
                height = None
            elif location == 'surface':
                height = depth
            elif location == 'ground':
                height = 0
            else:
                height, location = float(location), 'snow'
                if not 0 <= height <= depth:
                    raise ValueError(f'Invalid temperature height in {sheet} row {row}')
            records.append(dict(metadata, measurement='temperature', temperature_location=location,
                                temperature_height_cm=height, temperature_c=temperature))
    if not records:
        raise ValueError('No field-day observations found.')
    return records


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workbook', type=Path, default=WORKBOOK)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    records = extract(args.workbook)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as out:
        writer = csv.DictWriter(out, COLUMNS, lineterminator='\n')
        writer.writeheader()
        writer.writerows(records)
    print(f'Wrote {len(records)} measurements to {args.output}')
