#!/usr/bin/env python3
"""
@package
Generate a HTML BOM list.
Components are sorted and grouped by value
Fields are (if exist)
Ref, Quantity, Value, Part, Footprint, Description, Vendor

Command line:
python "pathToFile/bom_with_advanced_grouping.py" "%I" "%O.html"
"""
import argparse
import collections
import os
import subprocess
import sys

import yaml

cli = argparse.ArgumentParser()
cli.add_argument('sourcing')
cli.add_argument('netlist')
cli.add_argument('bomfile')
cli.add_argument('--footprint-aliases')
args = cli.parse_args()

# Import the KiCad python helper module and the csv formatter
sys.path.append('/usr/share/kicad/plugins')
import kicad_netlist_reader

def components_equal(self, other):
    """
    Returns True if the components are equivalent for BOM purposes
    """
    if self.getValue() != other.getValue():
        return False
    if self.getPartName() != other.getPartName():
        return False
    if self.getFootprint() != other.getFootprint():
        return False
    if self.getField("Tolerance") != other.getField("Tolerance"):
        return False
    if self.getField("Manufacturer") != other.getField("Manufacturer"):
        return False
    if self.getField("Voltage") != other.getField("Voltage"):
        return False
    if self.getField("MPN") != other.getField("MPN"):
        return False

    return True

kicad_netlist_reader.comp.__eq__ = components_equal

# read the netlist file
net = kicad_netlist_reader.netlist(args.netlist)

# read sourcing info
with open(args.sourcing) as sourcing_file:
    sourcing_info = yaml.load(sourcing_file, Loader=yaml.loader.SafeLoader)
    mpns = sourcing_info['products']
    distributors = sourcing_info['distributors']
    del sourcing_info

if args.footprint_aliases is not None:
    with open(args.footprint_aliases) as aliases_file:
        footprint_aliases = yaml.load(aliases_file, Loader=yaml.loader.SafeLoader)
else:
    footprint_aliases = {}

table_rows = [
    "<tr>"
        "<th>Ref</th>"
        "<th>Qnty</th>"
        "<th>Value</th>"
        "<th>Footprint</th>"
        "<th>MPN</th>"
        "<th>Total</th>"
    "</tr>"
]

components = net.getInterestingComponents()
dnp_items = collections.defaultdict(list)
comp_counter = 0
overall_price = 0

# iterate over components in groups of matching parts + values
for group in net.groupComponents(components):
    comp = group[-1]
    if comp.getField('DNP'):
        # component should not be placed
        dnp_items[comp.getField('DNP')].extend((c.getRef() for c in group))
        continue
    else:
        comp_counter += len(group)

    best_price = None
    links = []

    for distributor, info in mpns.get(comp.getField('MPN'), {}).items():
        price = info[1] * len(group)
        url = distributors[distributor] % (info[0],)
        links.append(f'<a href="{url}">{price:.2f}</a>')
        if best_price is None or best_price > price:
            best_price = price

    if best_price is not None:
        overall_price += best_price

    footprint = comp.getFootprint()
    footprint_alias = footprint_aliases.get(footprint)
    if footprint_alias is None:
        footprint_html = footprint
    else:
        footprint_html = f'<span title="{footprint}">{footprint_alias}</span>'

    table_rows.append(
        "<tr>"
            f"<td>{', '.join(comp.getRef() for comp in group)}</td>"
            f"<td>{len(group)}</td>"
            f"<td>{comp.getValue()}</td>"
            f"<td>{footprint_html}</td>"
            f"<td>{comp.getField('MPN')}</td>"
            f"<td>{', '.join(links)}</td>"
        "</tr>"
    )

dnp_list = []
for k, v in dnp_items.items():
    hint = ", ".join(v)
    dnp_list.append(f'<span title={hint}>{k}: {len(v)}</span>')

with open(args.bomfile, 'w') as bomfile:
    bomfile.write(f"""<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <title>BOM for {net.getSource()}</title>
    </head>
    <body>
        <h1>{net.getSource()}</h1>
        <p>{net.getDate()}</p>
        <p>{net.getTool()}</p>
        <p>Components:</p>
        <ul>
            <li>required: {comp_counter} ({overall_price:.2f} EUR)</li>
            <li>{f'</li>{os.linesep}            <li>'.join(dnp_list)}</li>
        </ul>
        <table>
            {(os.linesep + '            ').join(table_rows)}
        </table>
    </body>
</html>""")

subprocess.call(['xdg-open', args.bomfile])
