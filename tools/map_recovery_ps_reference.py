"""Bounded paired-single reference for the uploaded DOL's point-transform leaf.

This is deliberately NOT a general GameCube emulator. Only unquantized GQR0
loads/stores and four arithmetic operations used by that leaf are allowed.
Arithmetic uses Python binary64 intermediates rounded to binary32 per paired
operation; subnormal/NaN/FPSCR and exact fused tie behavior are outside scope.
No original executable bytes are included in this module.
"""
import math
import struct


def f32(value):
    result = struct.unpack('>f', struct.pack('>f', value))[0]
    if not math.isfinite(result):
        raise ValueError('Nonfinite reference arithmetic')
    return result


def point_transform_reference(code, point, matrix):
    """Interpret at most 32 instructions; read r3 point, r4 matrix, write r5 xyz.

    Matrix is four row vectors of four floats, including translation row.
    Unsupported memory access, quantization, opcode or missing return fails.
    """
    if len(point) != 3 or len(matrix) != 16 or len(code) % 4 or len(code) > 128:
        raise ValueError('Invalid point-reference input shape/budget')
    registers = {3: 0x1000, 4: 0x2000, 5: 0x3000}
    memory = {}
    for address, values in ((0x1000, point), (0x2000, matrix)):
        for i, value in enumerate(values):
            memory[address + i * 4] = f32(value)
    pairs = {}
    output = {}
    for offset in range(0, len(code), 4):
        word = struct.unpack_from('>I', code, offset)[0]
        if word == 0x4e800020:
            if offset + 4 != len(code) or set(output) != {0x3000, 0x3004, 0x3008}:
                raise ValueError('Reference return/output mismatch')
            return [output[0x3000 + i * 4] for i in range(3)]
        op = word >> 26
        d, a, b, c = ((word >> bit) & 31 for bit in (21, 16, 11, 6))
        if op in (56, 60):
            if (word >> 12) & 7 or a not in registers:
                raise ValueError('Unsupported reference quantization/register')
            displacement = word & 4095
            if displacement & 2048:
                displacement -= 4096
            address = registers[a] + displacement
            single = (word >> 15) & 1
            if op == 56:
                if a == 5 or any(address + i * 4 not in memory for i in range(1 if single else 2)):
                    raise ValueError('Reference read outside supplied inputs')
                pairs[d] = (memory[address], 1.0 if single else memory[address + 4])
            else:
                if a != 5 or d not in pairs:
                    raise ValueError('Invalid reference store')
                for i in range(1 if single else 2):
                    at = address + 4 * i
                    if at not in (0x3000, 0x3004, 0x3008) or at in output:
                        raise ValueError('Reference write outside/overlapping output')
                    output[at] = pairs[d][i]
        elif op == 4:
            xo = (word >> 1) & 31
            if word & 1 or xo not in (12, 14, 15, 21):
                raise ValueError('Unsupported paired arithmetic')
            try:
                if xo == 12:
                    result = [pairs[a][i] * pairs[c][0] for i in range(2)]
                elif xo in (14, 15):
                    lane = 0 if xo == 14 else 1
                    result = [pairs[a][i] * pairs[c][lane] + pairs[b][i] for i in range(2)]
                else:
                    result = [pairs[a][i] + pairs[b][i] for i in range(2)]
            except KeyError as error:
                raise ValueError('Reference uninitialized paired register') from error
            pairs[d] = tuple(f32(v) for v in result)
        else:
            raise ValueError(f'Unsupported reference opcode {op}')
    raise ValueError('Reference instruction budget exhausted without return')
