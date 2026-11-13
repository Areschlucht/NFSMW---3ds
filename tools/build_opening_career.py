#!/usr/bin/env python3
"""Recover source-bound original opening scripts and pack the native career flow.

Game bytecode/data stay in private generated output. This is not a complete Lua
VM; instruction and constant inspection retains the original control flow.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zlib

EVENT_IDS = ('16.1.0', '16.2.2', '16.2.3', '16.1.1', '16.2.1')
EVENT_KEYS = (0x42938ce2, 0xd348f2cd, 0x6ddd8383, 0x9f60a40e, 0xf7e4440a)
GAMEPLAY_SHA256 = '7ac98113d931cd90c68dbdb8e6ba94c643eef85a9af076a5f2e71ac4072d9ab6'
ATTRIBUTES_SHA256 = '5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c'
FRONTEND_SHA256 = 'adbb364d58f348ee95d2b59e99d0312b1bd8079d77be7bc76bd40461ee2cc9c2'


class Lua50:
    """Strict reader for observed GC-authored little-endian Lua5.0 float chunks."""
    def __init__(self, data):
        self.data = bytes(data)
        self.at = 0
        if self.take(14) != b'\x1bLuaP\x01\x04\x04\x04\x06\x08\x09\x09\x04':
            raise ValueError('Unsupported original Lua chunk format')
        if self.take(4) != bytes.fromhex('3bafef4b'):
            raise ValueError('Unexpected original Lua number signature')
        self.root = self.function(0)
        if self.at != len(self.data):
            raise ValueError('Trailing Lua data')

    def take(self, n):
        if n < 0 or self.at + n > len(self.data):
            raise ValueError('Truncated Lua chunk')
        out = self.data[self.at:self.at+n]
        self.at += n
        return out

    def integer(self):
        return struct.unpack('<I', self.take(4))[0]

    def count(self):
        n = self.integer()
        if n > 65536:
            raise ValueError('Lua count exceeds bounded inspection')
        return n

    def string(self):
        n = self.count()
        if not n:
            return None
        s = self.take(n)
        if s[-1] or b'\0' in s[:-1]:
            raise ValueError('Lua string boundary')
        return s[:-1].decode('ascii')

    def function(self, depth):
        if depth > 8:
            raise ValueError('Lua prototype nesting')
        source = self.string()
        line = self.integer()
        nups, parameters, vararg, stack = self.take(4)
        lines = [self.integer() for _ in range(self.count())]
        locals_ = [{'name': self.string(), 'start': self.integer(), 'end': self.integer()}
                   for _ in range(self.count())]
        upvalues = [self.string() for _ in range(self.count())]
        constants = []
        for _ in range(self.count()):
            tag = self.take(1)[0]
            if tag == 0:
                constants.append(None)
            elif tag == 3:
                constants.append(struct.unpack('<f', self.take(4))[0])
            elif tag == 4:
                constants.append(self.string())
            else:
                raise ValueError(f'Unsupported original Lua constant tag {tag}')
        children = [self.function(depth+1) for _ in range(self.count())]
        instructions = [self.integer() for _ in range(self.count())]
        return {'source': source, 'line': line, 'nups': nups, 'parameters': parameters,
                'vararg': vararg, 'stack': stack, 'lines': lines, 'locals': locals_,
                'upvalues': upvalues, 'constants': constants, 'children': children,
                'instructions': instructions}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def trace_lua(proto, arguments, globals_, budget=4096):
    """Bounded Lua5.0 subset interpreter for inspection against supplied mocks.

    This never executes embedded native code or opens files from game scripts.
    Unsupported instructions fail. All callable values come from the caller's
    explicit test dictionary; no Python eval/import/environment is exposed.
    """
    registers = [None]*256
    for i, v in enumerate(arguments):
        registers[i] = v
    code, constants = proto['instructions'], proto['constants']
    def rk(v):
        return constants[v-250] if v >= 250 else registers[v]
    def truth(v):
        return v is not None and v is not False
    def get(table, key):
        if not isinstance(table, dict):
            raise ValueError('Inspection fixture lacks original table')
        return table.get(key)
    pc = 0
    for _ in range(budget):
        if not 0 <= pc < len(code):
            raise ValueError('Lua inspection PC escaped prototype')
        w = code[pc]
        pc += 1
        op, a, b, c = w & 63, w >> 24, (w >> 15) & 511, (w >> 6) & 511
        bx = (w >> 6) & 262143
        if op == 0:
            registers[a] = registers[b]
        elif op == 1:
            registers[a] = constants[bx]
        elif op == 2:
            registers[a] = bool(b)
            pc += bool(c)
        elif op == 3:
            for i in range(a, b+1):
                registers[i] = None
        elif op == 5:
            registers[a] = get(globals_, constants[bx])
        elif op == 6:
            registers[a] = get(registers[b], rk(c))
        elif op == 9:
            registers[a][rk(b)] = rk(c)
        elif op == 11:
            obj = registers[b]
            registers[a+1], registers[a] = obj, get(obj, rk(c))
        elif op == 18:
            registers[a] = not truth(registers[b])
        elif op == 20:
            pc += bx-131071
        elif op == 21:
            pc += (rk(b) == rk(c)) != bool(a)
        elif op == 24:
            if truth(registers[b]) == bool(c):
                registers[a] = registers[b]
            else:
                pc += 1
        elif op == 25:
            fn = registers[a]
            if not callable(fn) or not b or c not in (1, 2):
                raise ValueError('Unsupported original Lua inspection call')
            result = fn(*registers[a+1:a+b])
            if c == 2:
                registers[a] = result
        elif op == 27:
            if b != 1:
                raise ValueError('Unexpected inspection return values')
            return
        else:
            raise ValueError(f'Unsupported Lua inspection opcode {op}')
    raise ValueError('Lua inspection instruction budget')


def verify_script_paths(scripts):
    by_name = {s['name']: s['prototype']['children'][0] for s in scripts}
    methods = ('SetTimer', 'KillTimer', 'ForceAIControl', 'ClearAIControl',
               'SabotageEngine', 'SetCopsEnabled', 'SpawnCop', 'NoNewPursuitsOrCops',
               'JumpToCarLot', 'DisableBarriers', 'EnableBinBarriers', 'DoSpecialFinalization',
               'SetRoaming')
    functions = ('ECellCall', 'EPlayRaceMovie', 'ChangeState', 'E911Call', 'EBailPursuit',
                 'EDispIntroRace', 'EFadeScreenNoLoadingBarOn', 'EFadeScreenNoLoadingBarOff', 'Fade')
    def run(name, *, sender=None, player=True, definition=None, context=None, timer=None):
        calls = []
        def logger(name):
            def call(*args):
                calls.append([name, list(args)])
            return call
        game = {n: logger('Game.'+n) for n in methods}
        game['GetPlayerElement'] = lambda index: 'PLAYER'+str(int(index))
        env = {n: logger(n) for n in functions}
        env.update(Game=game, Debug={'Print': lambda *args: None})
        message = {'Sender': sender, 'Element': {'IsPlayer': lambda self: player}, 'Name': timer}
        defaults = {n: n for n in ('call_from_mia', 'kill_engine', 'cop_spawn_trigger', 'cop_spawn_1', 'cop_spawn_2', 'bail_trigger', 'bail_pursuit', 'trigger_911')}
        defaults.update(definition or {})
        trace_lua(by_name[name], [defaults, message, context or {}], env)
        return calls
    checks = []
    for player in (False, True):
        for sender in ('cop_spawn_trigger', 'bail_pursuit', 'trigger_911', 'other'):
            calls = run('stategraph_basicrace_racing_handler_triggerenter_12', sender=sender, player=player)
            expected = []
            if player and sender == 'cop_spawn_trigger':
                expected = [['Game.SetCopsEnabled', [True]], ['Game.SpawnCop', ['cop_spawn_1', 'copmidsize', False, False]], ['Game.SpawnCop', ['cop_spawn_2', 'copmidsize', False, False]]]
            elif player and sender == 'bail_pursuit':
                expected = [['EBailPursuit', [1.0, 1.0]], ['Game.NoNewPursuitsOrCops', []]]
            elif player and sender == 'trigger_911':
                expected = [['E911Call', []]]
            if calls != expected:
                raise AssertionError(('Original police script differs', player, sender, calls))
            checks.append({'script': 'triggerenter_12', 'player': player, 'sender': sender, 'calls': calls})
    for player in (False, True):
        calls = run('stategraph_basicrace_racing_handler_triggerenter_10', sender='kill_engine', player=player)
        expected = [['Game.KillTimer', ['backup']], ['Game.SabotageEngine', ['PLAYER0', 5.0]]] if player else []
        if calls != expected:
            raise AssertionError(('Original sabotage differs', calls))
        checks.append({'script': 'triggerenter_10', 'player': player, 'sender': 'kill_engine', 'calls': calls})
    calls = run('stategraph_basicrace_racing_handler_notifyengineblown_2')
    if calls != [['Game.SetTimer', ['eblown', 1.0]]]:
        raise AssertionError('Original engine-blown timer differs')
    checks.append({'script': 'notifyengineblown_2', 'calls': calls})
    calls = run('stategraph_basicrace_racing_handler_notifycellcallstarted', context={'WaitForCallLoad': True})
    if calls != [['Game.SetTimer', ['fade', 8.0]]]:
        raise AssertionError(('Original call-start timer differs', calls))
    checks.append({'script': 'notifycellcallstarted', 'calls': calls})
    for timer in ('fade', 'killrace'):
        calls = run('stategraph_basicrace_racing_handler_notifytimer', timer=timer)
        if timer == 'fade' and calls != [['Game.SetTimer', ['killrace', 3.0]], ['Game.KillTimer', ['fade']], ['Game.ForceAIControl', [0.0]], ['Game.ForceAIControl', [1.0]], ['EFadeScreenNoLoadingBarOn', []]]:
            raise AssertionError(('Original partial fade differs', calls))
        if timer == 'killrace' and calls[-1] != ['ChangeState', ['postrace']]:
            raise AssertionError(('Original partial postrace differs', calls))
        checks.append({'script': 'notifytimer', 'timer': timer, 'calls': calls})
    for name, property_, target in (('intromovie', 'IntroMovie', 'intronis'), ('outromovie', 'OutroMovie', 'done')):
        for asset in ('', 'storyfmv_example'):
            calls = run('stategraph_basicrace_'+name+'_handler_stateenter', definition={property_: asset})
            expected = [['EPlayRaceMovie', [asset]]] if asset else [['ChangeState', [target]]]
            if calls != expected:
                raise AssertionError(('Original conditional movie differs', name, asset, calls))
            checks.append({'script': name, 'asset': asset, 'calls': calls})
    calls = run('stategraph_basicrace_done_handler_stateenter_2')
    if calls != [['Game.JumpToCarLot', []]]:
        raise AssertionError('Original final car-lot dispatch differs')
    checks.append({'script': 'done_handler_stateenter_2', 'calls': calls})
    return checks


def inspect_scripts(stategraphs, gameplay):
    from nfs_huff_reference import decode
    rows = []
    for row in stategraphs:
        field = row['fields'].get('0x9a4a020a')
        if not field:
            continue
        if field['type'] != 'Attrib::Blob' or field['source_sha256'] != digest(gameplay):
            raise ValueError('Script field source identity')
        size, pointer = struct.unpack('>II', bytes.fromhex(field['value']['raw_hex']))
        start = field['file_offset'] - field['stream_offset'] + pointer
        if not 0 <= start < start + size <= len(gameplay):
            raise ValueError('Script range')
        encoded = gameplay[start:start+size]
        if len(encoded) < 16 or encoded[:4] not in (b'HUFF', b'JDLZ'):
            raise ValueError('Unsupported original script envelope')
        expected = struct.unpack_from('<I', encoded, 8)[0]
        if expected > 256*1024:
            raise ValueError('Script exceeds observed budget')
        trailer = b''
        if encoded[:4] == b'HUFF':
            decoded = decode(encoded, expected)
        else:
            from frontend_flow_inventory import frontend_jdlz
            decoded, trailer = frontend_jdlz(encoded)
            if len(decoded) != expected:
                raise ValueError('Unexpected JDLZ script size')
        rows.append({'key': row['key'], 'name': row['name'],
                     'source_sha256': field['source_sha256'],
                     'compressed_offset': start, 'compressed_bytes': size,
                     'compressed_sha256': digest(encoded),
                     'unused_jdlz_trailer_hex': trailer.hex(),
                     'decoded_bytes': len(decoded), 'decoded_sha256': digest(decoded),
                     'prototype': Lua50(decoded).root})
    return rows


def generate(attributes, gameplay, dol, frontend, output):
    from gameplay_packages import GameplayPackages, dol_labels
    from vehicle_attributes import VehicleAttributes
    from vehicle_dol import DolImage
    from vehicle_ppc_reference import DOL_SHA256
    from vehicle_vlt_hash import vlt_hash
    if (digest(dol) != DOL_SHA256 or digest(gameplay) != GAMEPLAY_SHA256 or
            digest(attributes) != ATTRIBUTES_SHA256 or digest(frontend) != FRONTEND_SHA256):
        raise ValueError('Unexpected original USA source set')
    image = DolImage(dol)
    original_ids = tuple(image.c_string(0x803ec79c+i*8) for i in range(5))
    if original_ids != EVENT_IDS:
        raise ValueError('Original ordered career ID table differs')
    labels = [*dol_labels(dol), 'Cost', 'UnlockedAt', 'CashValue', 'IntroNIS', 'OutroNIS', 'NISShell', 'PostRaceActivity']
    schema = VehicleAttributes(attributes, labels=labels)
    gp = GameplayPackages(gameplay, schema, labels)
    fe = VehicleAttributes(frontend, labels=labels, dependency=schema)
    db = gp.databases['gpcore']
    rows = {key: row for (_, key), row in db.collections.items()}
    classes = {key: cls for (cls, key) in db.collections}
    all_rows = {}
    for package in gp.databases.values():
        for (_, key), row in package.collections.items():
            if key in all_rows:
                raise ValueError('Ambiguous original collection key')
            all_rows[key] = package, row

    def fields(key):
        owner, row = all_rows[key]
        return {f['field_key']: f for f in owner.fields(row).values()}

    def value(f, name, default=None):
        key = int(name, 16) if name.startswith('0x') else vlt_hash(name)
        return f.get(key, {}).get('value', default)

    def key_value(f, name):
        v = value(f, name, {})
        return int(v.get('raw_hex', '0'), 16)

    strings = bytearray(b'\0')
    offsets = {'': 0}
    def string(s):
        if s not in offsets:
            encoded = s.encode('ascii')
            if not encoded or b'\0' in encoded:
                raise ValueError('Invalid original text')
            offsets[s] = len(strings)
            strings.extend(encoded+b'\0')
        return offsets[s]

    stategraphs = []
    for key, row in rows.items():
        if db.label(key).startswith('stategraph'):
            stategraphs.append({'key': f'{key:08x}', 'name': db.label(key), 'class': db.label(classes[key]), 'fields': db.fields(row)})
    scripts = inspect_scripts(stategraphs, gameplay)
    script_checks = verify_script_paths(scripts)
    by_name = {s['name']: s for s in scripts}
    def constants(name):
        return by_name[name]['prototype']['children'][0]['constants']
    # Timings bind to actual script constants, never remembered game values.
    if (8.0 not in constants('stategraph_basicrace_racing_handler_notifycellcallstarted') or
            3.0 not in constants('stategraph_basicrace_racing_handler_notifytimer') or
            1.0 not in constants('stategraph_basicrace_racing_handler_notifyengineblown_2')):
        raise ValueError('Original scripted opening timers differ')
    stages = []
    evidence = []
    for i, (identifier, key) in enumerate(zip(EVENT_IDS, EVENT_KEYS)):
        f = fields(key)
        if value(f, '0xa78403ec') != identifier:
            raise ValueError('Original event ID/key association differs')
        preset = value(f, '0xc0eeb909', '')
        if preset != 'M3GTRCAREERSTART':
            raise ValueError('Unexpected original opening preset')
        outro_nis = value(f, 'OutroNIS', '')
        linked = key_value(f, 'PostRaceActivity')
        if i == 3:
            shell = fields(linked)
            if linked != 0x04b06f54 or value(shell, 'NISShell') is not True or key_value(shell, 'PostRaceActivity') != EVENT_KEYS[4]:
                raise ValueError('Original intermediate NIS shell differs')
            outro_nis = value(shell, 'OutroNIS', '')
        trigger = 0x40caf8c1 if i == 0 else 0xf73bbbcb if i == 4 else 0
        reward = value(f, 'CashValue')
        if reward != (10000.0 if 1 <= i <= 3 else 0.0):
            raise ValueError('Original opening prize differs')
        row = (key, 1 if i == 0 else 2 if i == 4 else 0, linked,
               string(value(f, 'IntroMovie', '')), string(value(f, 'OutroMovie', '')),
               string(value(f, 'IntroNIS', '')), string(outro_nis), trigger, string(preset), int(reward))
        stages.append(struct.pack('<10I', *row)+bytes(24))
        evidence.append({'event': f'{key:08x}', 'source_id': identifier, 'source_name': db.label(key),
                         'preset': preset, 'intro_movie': value(f, 'IntroMovie', ''),
                         'outro_movie': value(f, 'OutroMovie', ''), 'intro_nis': value(f, 'IntroNIS', ''),
                         'outro_nis': outro_nis, 'linked_event': f'{linked:08x}',
                         'scripted_trigger': f'{trigger:08x}', 'reward': int(reward), 'source_fields': f})
    cars = []
    car_evidence = []
    for (_, key), row in fe.collections.items():
        f = {v['field_key']: v for v in fe.fields(row).values()}
        cost = value(f, 'Cost', 0)
        if value(f, 'UnlockedAt') != 16 or cost <= 0:
            continue
        model = fe.label(key)
        cars.append(struct.pack('<4I', key, cost, 16, string(model))+bytes(48))
        car_evidence.append({'key': f'{key:08x}', 'model': model, 'cost': cost, 'unlocked_at': 16, 'source_fields': f})
    if len(cars) != 4 or {x['model'] for x in car_evidence} != {'gti', 'is300', 'cobaltss', 'punto'}:
        raise ValueError('Original initial unlock roster differs')
    triggers = []
    trigger_evidence = []
    police = []
    for key, (owner, _) in all_rows.items():
        name = owner.label(key)
        if key not in (0x40caf8c1, 0xf73bbbcb):
            if not name.startswith(('16_1_0_partial_dday/', '16_2_1_d_day_intro/', '16_2_3_sprint/')) or not any(t in name for t in ('cop_spawn', 'bail_', 'trigger_911')):
                continue
        f = fields(key)
        position = value(f, 'Position')
        if position is None:
            continue
        rotation, dimensions, radius, width = value(f, 'Rotation'), value(f, 'Dimensions'), value(f, 'Radius'), value(f, 'Width')
        present = 1 | (2 if rotation is not None else 0) | (4 if dimensions is not None else 0) | (8 if radius is not None else 0) | (16 if width is not None else 0)
        node = {'key': f'{key:08x}', 'name': name, 'present': present, 'position': position,
                'rotation': rotation or 0, 'dimensions': dimensions or [0, 0, 0], 'radius': radius or 0, 'width': width or 0,
                'source_fields': f}
        if key in (0x40caf8c1, 0xf73bbbcb):
            trigger_evidence.append(node)
        else:
            police.append(node)
    for node in sorted(trigger_evidence, key=lambda n: n['key']):
        triggers.append(struct.pack('<II9f', int(node['key'], 16), node['present'], *node['position'], node['rotation'], *node['dimensions'], node['radius'], node['width'])+bytes(20))
    if len(triggers) != 2:
        raise ValueError('Original scripted opening trigger absent: '+str([(x['key'], x['name']) for x in trigger_evidence]))
    data = bytearray(160)+b''.join(stages+cars+triggers)+strings
    struct.pack_into('<4s11I', data, 0, b'NFC1', 1, len(data), 0, 5, 4, 2, 160, 480, 736, 864, len(strings))
    data[64:96], data[96:128], data[128:160] = bytes.fromhex(gp.sha256), bytes.fromhex(fe.sha256), bytes.fromhex(DOL_SHA256)
    struct.pack_into('<I', data, 12, zlib.crc32(data[16:]))
    output.mkdir(parents=True, exist_ok=True)
    path = output/'opening-career.nfc'
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Existing career pack differs')
    if not path.exists():
        path.write_bytes(data)
    report = {'schema': 1, 'source_sha256': {'gameplay': gp.sha256, 'frontend': fe.sha256, 'dol': DOL_SHA256},
              'opening_order_selector': {'start': '801a4cb0', 'end_exclusive': '801a4d2c', 'sha256': digest(image.read(0x801a4cb0, 0x7c)), 'string_table': '803ec79c'},
              'stages': evidence, 'cars': car_evidence, 'scripted_triggers': trigger_evidence,
              'opening_police_nodes': police, 'scripts': scripts, 'script_path_checks': script_checks,
              'initial_wallet_recovered': True, 'initial_cash': 0,
              'wallet_consumers': {'new_profile_caller': '8013c494', 'career_constructor': '8015fcd4', 'rank_one_gate': '801c3a48', 'cash_value_getter': '801a4f3c', 'wallet_add': '801c3b28'},
              'pack': {'bytes': len(data), 'sha256': digest(data)},
              'limits': ['Native lifecycle is not the complete original Lua VM', 'Actual calls/movie/NIS/engine notifications remain caller-owned', 'No initial money or ownership is fabricated', 'Original police AI and pursuit scheduler remain separate']}
    (output/'opening-evidence.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stategraphs', type=Path)
    parser.add_argument('--gameplay', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--attributes', type=Path)
    parser.add_argument('--frontend', type=Path)
    parser.add_argument('--dol', type=Path)
    args = parser.parse_args()
    if args.stategraphs:
        result = inspect_scripts(json.loads(args.stategraphs.read_text()), args.gameplay.read_bytes())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({'scripts': len(result), 'decoded_bytes': sum(x['decoded_bytes'] for x in result)}))
    else:
        if not all((args.attributes, args.frontend, args.dol)):
            parser.error('native pack generation requires --attributes --frontend --dol')
        result = generate(args.attributes.read_bytes(), args.gameplay.read_bytes(), args.dol.read_bytes(), args.frontend.read_bytes(), args.output)
        print(json.dumps({'stages': len(result['stages']), 'cars': len(result['cars']), 'pack': result['pack']}))
