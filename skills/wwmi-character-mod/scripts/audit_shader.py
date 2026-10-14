"""Read-only triage of exported shader assembly; reports clues, not diagnoses."""
import argparse
import json
from pathlib import Path
import re


REGISTER = r'r\d+\.[xyzw]'


def audit(path, context=4):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    gates, discards, min_combinations = [], [], []
    for index, line in enumerate(lines):
        instruction = line.strip()
        if not instruction or instruction.startswith('//'):
            continue
        gate = re.search(r'ld_indexable\(texture1d\).*?l\((\d+),\s*0\),\s*t120\.', instruction)
        if gate:
            gates.append({'line': index + 1, 'parameter_index': int(gate[1]),
                          'instruction': instruction})
        if re.match(r'discard_(?:nz|z)\b', instruction):
            start = max(0, index - context)
            discards.append({'line': index + 1, 'instruction': instruction,
                             'preceding': [{'line': n + 1, 'instruction': lines[n].strip()}
                                           for n in range(start, index)]})
        if re.fullmatch(rf'min {REGISTER}, {REGISTER}, {REGISTER}', instruction):
            min_combinations.append({'line': index + 1, 'instruction': instruction})
    return {'path': str(path.resolve()), 'line_count': len(lines),
            'ini_parameter_reads': gates, 'register_min_combinations': min_combinations,
            'discards': discards,
            'interpretation': 'Static clues only. Trace data sources and actual draw scope; '
                              'min need not be visibility, and t120 reads do not prove gate activation.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('shaders', type=Path, nargs='+', help='Exported assembly text files')
    parser.add_argument('--context', type=int, default=4, help='Lines preceding each discard (0-30)')
    args = parser.parse_args()
    if not 0 <= args.context <= 30:
        parser.error('--context must be between 0 and 30')
    try:
        results = [audit(path, args.context) for path in args.shaders]
    except (OSError, UnicodeError) as exc:
        parser.exit(1, f'Cannot audit shader: {exc}\n')
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
