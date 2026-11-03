"""Bounded original 0x802EF290 PPC candidate query. Optional Unicorn dependency.

Only the uploaded USA executable revision is accepted; no game bytes bundled.
Skip only paired-single f31 stack save/restore (incoming callee-saved register
has no effect on this leaf's output). Original scalar arithmetic/branches run.
This is not a complete GameCube emulator or a complete collision solver.
"""
import hashlib
import struct
from map_recovery_dol import DolImage


class OriginalStripReference:
    ADDRESS = 0x802ef290
    END = 0x802efb7c

    def __init__(self, raw):
        from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
        from unicorn import ppc_const as reg
        self.reg = reg
        self.dol = DolImage(raw)
        self.routine_sha256 = hashlib.sha256(self.dol.read(self.ADDRESS, self.END-self.ADDRESS)).hexdigest()
        if self.dol.sha256 != '33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166':
            raise ValueError('Unverified original executable revision')
        u = self.u = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
        u.mem_map(0x80000000, 0x600000)
        for s in self.dol.sections:u.mem_write(s['address'], self.dol.read(s['address'], s['size']))
        u.mem_map(0x60000000, 0x10000)
        u.mem_map(0x70000000, 0x10000)
        u.reg_write(reg.UC_PPC_REG_MSR, u.reg_read(reg.UC_PPC_REG_MSR) | (1 << 13))
        u.hook_add(UC_HOOK_CODE, self._hook)

    def _hook(self, u, address, size, data):
        if address in (0x802ef294, 0x802efb70):u.reg_write(self.reg.UC_PPC_REG_PC, address + 4)
        elif not self.ADDRESS <= address < self.END:raise ValueError(f'Reference escaped at {address:08x}')

    def query(self, point, center, strip, mask=0):
        if len(strip) < 24 or len(strip) > 0xc000:raise ValueError('Invalid reference strip length')
        count = struct.unpack_from('>H', strip, 6)[0]
        if count < 3 or count * 8 != len(strip):raise ValueError('Invalid reference vertex count')
        u, reg = self.u, self.reg
        u.mem_write(0x60000000, struct.pack('>I', mask))
        u.mem_write(0x60000100, struct.pack('>3f', *point))
        u.mem_write(0x60000200, struct.pack('>3f', *center))
        u.mem_write(0x60001000, strip)
        u.mem_write(0x60000400, bytes(64))
        for register, value in ((reg.UC_PPC_REG_1, 0x7000ff00),
            (reg.UC_PPC_REG_3, 0x60000000), (reg.UC_PPC_REG_4, 0x60000100),
            (reg.UC_PPC_REG_5, 0x60000200), (reg.UC_PPC_REG_6, 0x60001000),
            (reg.UC_PPC_REG_7, 0x60000400), (reg.UC_PPC_REG_LR, 0x6000fff0)):
            u.reg_write(register, value)
        u.emu_start(self.ADDRESS, 0x6000fff0, timeout=100000, count=100000)
        if u.reg_read(reg.UC_PPC_REG_PC) != 0x6000fff0:raise ValueError('Reference budget exceeded')
        raw = bytes(u.mem_read(0x60000400, 48))
        return dict(hit=bool(u.reg_read(reg.UC_PPC_REG_3)),
                    vertices=[list(struct.unpack_from('>3f', raw, i*16)) for i in range(3)],
                    material_index=raw[44], attributes=raw[45])
