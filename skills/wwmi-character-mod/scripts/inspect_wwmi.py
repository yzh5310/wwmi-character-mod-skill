"""Read only the WWMI paths and diagnostic settings needed for a mod task."""
import argparse
import json
import os
from pathlib import Path
import re


def inspect(config_path):
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    wwmi = config['Importers']['WWMI']
    raw_root = os.path.expandvars(wwmi['Importer']['importer_folder'])
    root = Path(raw_root).expanduser()
    if not root.is_absolute():
        raise ValueError('Relative importer_folder is ambiguous; resolve its launcher base first.')
    ini = root / 'd3dx.ini'
    text = ini.read_text(encoding='utf-8-sig')
    keys = ['hunting', 'toggle_hunting', 'analyse_frame', 'analyse_options',
            'export_fixed', 'export_shaders', 'export_hlsl', 'exclude_recursive']
    settings = {}
    for key in keys:
        values = re.findall(rf'^\s*{key}\s*=\s*([^\r\n]*)', text, re.M | re.I)
        if values:
            settings[key] = values[0] if len(values) == 1 else values
    mods = root / 'Mods'
    hunting = settings.get('hunting')
    analysis_options = settings.get('analyse_options', '')
    if not isinstance(analysis_options, str):
        analysis_options = ' '.join(analysis_options)
    broad_dump_flags = sorted(set(analysis_options.split()) &
                              {'dump_rt', 'dump_tex', 'dump_cb', 'dump_vb', 'dump_ib'})
    capture_preflight = {
        'configured_hunting_state': {
            '0': 'disabled', '1': 'enabled_in_config',
            '2': 'soft_disabled_requires_runtime_toggle',
        }.get(hunting if isinstance(hunting, str) else '', 'unknown_or_ambiguous'),
        'analyse_frame_binding': settings.get('analyse_frame'),
        'global_resource_dump_flags': broad_dump_flags,
        'runtime_verified': False,
        'note': 'F10 reload is not frame analysis. Explicit dump commands require active analysis; verify the actual binding, foreground, target draw and new output files.',
    }
    return {
        'config_path': str(config_path.resolve()),
        'importer_root': str(root.resolve()),
        'game_folder': wwmi['Importer'].get('game_folder'),
        'enable_hunting': wwmi.get('Migoto', {}).get('enable_hunting'),
        'mods_directory': str(mods),
        'mods_directory_exists': mods.is_dir(),
        'ini_settings': settings,
        'capture_preflight': capture_preflight,
        'top_level_mod_folders': sorted(p.name for p in mods.iterdir() if p.is_dir()) if mods.is_dir() else [],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path,
                        default=Path(os.environ.get('APPDATA', Path.home() / 'AppData/Roaming'))
                        / 'XXMI Launcher/XXMI Launcher Config.json')
    args = parser.parse_args()
    try:
        result = inspect(args.config)
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(1, f'Cannot inspect WWMI: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
