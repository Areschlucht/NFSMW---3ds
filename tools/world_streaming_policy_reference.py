"""Execute original model binding and section fallback stages under strict bounds."""
import hashlib
import struct

from map_recovery_dol import DolImage
from world_render_recovery_reference import DOL_SHA256


def reference(dol_bytes, *, slots=None, identifier=None, available_ids=(), section_span=10):
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn import ppc_const as reg
    if hashlib.sha256(dol_bytes).hexdigest() != DOL_SHA256:
        raise ValueError('Reference requires verified USA executable')
    image = DolImage(dol_bytes)
    machine = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    machine.mem_map(0x10000000, 0x20000)
    machine.mem_map(0x80410000, 0x40000)
    machine.reg_write(reg.UC_PPC_REG_1, 0x1001E000)
    machine.reg_write(reg.UC_PPC_REG_LR, 0x1001F000)
    allocation = [0x10010000]
    if slots is not None:
        entry, stop = 0x802BDBE0, 0x802BDCE4
        stubs = (0x80060100, 0x800F663C)
        record = 0x10001000
        machine.mem_write(record+24, struct.pack('>4I', *slots))
        for n, value in ((8, 0), (19, 0x80420000), (20, 0x80430000),
                         (22, 0xBE43EDBB), (23, 0x90F70174), (31, record)):
            machine.reg_write(getattr(reg, f'UC_PPC_REG_{n}'), value)
    else:
        entry, stop = 0x802B9184, 0x1001F000
        stubs = ()
        if len(available_ids)*92 > 0x1B000:
            raise ValueError('Reference source-table budget exceeded')
        machine.mem_write(0x10000000, struct.pack('>II', 0x10002000, len(available_ids)))
        for i, value in enumerate(available_ids):
            machine.mem_write(0x10002000+i*92+8, struct.pack('>h', value))
        machine.mem_write(0x80437068, struct.pack('>I', section_span))
        machine.reg_write(reg.UC_PPC_REG_3, 0x10000000)
        machine.reg_write(reg.UC_PPC_REG_4, identifier & 0xFFFFFFFF)
    low = 0x802B9000 if slots is None else entry & ~4095
    high = 0x802BA000 if slots is None else 0x802BE000
    machine.mem_map(low, high-low)
    machine.mem_write(low, image.read(low, high-low))
    for address in stubs:
        machine.mem_map(address & ~4095, 4096)
    state = {'stopped': False, 'allocations': 0}

    def hook(uc, address, size, _):
        if address == stop:
            state['stopped'] = True
            uc.emu_stop()
        elif address in stubs:
            if address == 0x80060100:
                uc.reg_write(reg.UC_PPC_REG_3, allocation[0])
                allocation[0] += 32
                state['allocations'] += 1
            else:
                pointer = uc.reg_read(reg.UC_PPC_REG_3)
                key = uc.reg_read(reg.UC_PPC_REG_4)
                uc.mem_write(pointer+8, struct.pack('>I', key))
            uc.reg_write(reg.UC_PPC_REG_PC, uc.reg_read(reg.UC_PPC_REG_LR))
        elif not low <= address < high:
            raise ValueError(f'Unexpected original policy instruction {address:08x}')
    machine.hook_add(UC_HOOK_CODE, hook)
    machine.emu_start(entry, stop+4, count=100000)
    if not state['stopped']:
        raise ValueError('Original policy instruction budget exceeded')
    if slots is None:
        value = machine.reg_read(reg.UC_PPC_REG_3)
        return value - 2**32 if value >= 2**31 else value
    pointers = struct.unpack('>4I', machine.mem_read(record+40, 16))
    return [struct.unpack('>I', machine.mem_read(p+8, 4))[0] if p else None for p in pointers], state['allocations']


def polygon_reference(dol_bytes, point, points):
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn import ppc_const as reg
    if hashlib.sha256(dol_bytes).hexdigest() != DOL_SHA256:
        raise ValueError('Reference requires verified USA executable')
    if not 3 <= len(points) <= 16:
        raise ValueError('Original region vertex budget exceeded')
    image = DolImage(dol_bytes)
    machine = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
    machine.mem_map(0x802BF000, 4096)
    machine.mem_write(0x802BFF3C, image.read(0x802BFF3C, 0xBC))
    machine.mem_map(0x10000000, 4096)
    machine.mem_write(0x10000000, struct.pack('>2f', *point))
    machine.mem_write(0x10000100, b''.join(struct.pack('>2f', *p) for p in points))
    for n, value in ((3, 0x10000000), (4, 0x10000100), (5, len(points))):
        machine.reg_write(getattr(reg, f'UC_PPC_REG_{n}'), value)
    machine.reg_write(reg.UC_PPC_REG_MSR, 0x2000)
    machine.reg_write(reg.UC_PPC_REG_LR, 0x10000F00)
    state = {'stopped': False}

    def hook(uc, address, size, _):
        if address == 0x10000F00:
            state['stopped'] = True
            uc.emu_stop()
        elif not 0x802BFF3C <= address <= 0x802BFFF4:
            raise ValueError('Original polygon execution escaped bounded function')
    machine.hook_add(UC_HOOK_CODE, hook)
    machine.emu_start(0x802BFF3C, 0x10000F04, count=10000)
    if not state['stopped']:
        raise ValueError('Original polygon instruction budget exceeded')
    return bool(machine.reg_read(reg.UC_PPC_REG_3))


class ContainingSelectorReference:
    """Stateful original 802C1094 contained-point path with real region rows."""
    def __init__(self, dol_bytes, regions):
        from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
        from unicorn import ppc_const as reg
        if hashlib.sha256(dol_bytes).hexdigest()!=DOL_SHA256:
            raise ValueError('Reference requires verified USA executable')
        self.reg=reg
        self.machine=uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        image=DolImage(dol_bytes)
        for base,size in ((0x802BF000,0x3000),(0x80060000,0x2000),(0x80409000,0x1000)):
            uc.mem_map(base,size)
            uc.mem_write(base,image.read(base,size))
        uc.mem_map(0x10000000,0x80000)
        uc.reg_write(reg.UC_PPC_REG_MSR,0x2000)
        for head in (0x10000000,0x10000008,0x10000010):
            uc.mem_write(head,struct.pack('>II',head,head))
        polygon_pointers={}
        for i,polygon in enumerate(regions['polygons']):
            address=0x10010000+i*256
            if i>=768:
                raise ValueError('Reference polygon budget exceeded')
            polygon_pointers[polygon['id']]=address
            uc.mem_write(address+8,struct.pack('>hBB',polygon['id'],len(polygon['points']),polygon['flags']))
            uc.mem_write(address+12,struct.pack('>4f',*polygon['bounds']))
            uc.mem_write(address+36,b''.join(struct.pack('>2f',*p) for p in polygon['points']))
        self.address_ids={}
        head=0x10000010
        rows=regions['dependencies']
        if len(rows)>768:
            raise ValueError('Reference dependency budget exceeded')
        for i,dependency in enumerate(rows):
            address=0x10040000+i*256
            self.address_ids[address]=dependency['id']
            previous=address-256 if i else head
            following=address+256 if i+1<len(rows) else head
            uc.mem_write(address,struct.pack('>IIIh',following,previous,polygon_pointers[dependency['id']],dependency['id']))
        if rows:
            uc.mem_write(head,struct.pack('>II',0x10040000,0x10040000+(len(rows)-1)*256))
        self.stopped=False

        def hook(machine,address,size,_):
            if address==0x1007F000:
                self.stopped=True
                machine.emu_stop()
            elif address==0x802C0F00:
                raise ValueError('Original nearest-region stage required')
            elif not (0x802BF000<=address<0x802C2000 or 0x80060000<=address<0x80062000):
                raise ValueError('Original selector escaped bounded code')
        uc.hook_add(UC_HOOK_CODE,hook)

    def select(self,point):
        uc,reg=self.machine,self.reg
        uc.mem_write(0x1007D000,struct.pack('>2f',*point))
        for register,value in ((1,0x1007E000),(3,0x10000000),(4,0x1007D000)):
            uc.reg_write(getattr(reg,f'UC_PPC_REG_{register}'),value)
        uc.reg_write(reg.UC_PPC_REG_LR,0x1007F000)
        self.stopped=False
        uc.emu_start(0x802C1094,0x1007F004,count=100000)
        if not self.stopped:
            raise ValueError('Original selector instruction budget exceeded')
        return self.address_ids[uc.reg_read(reg.UC_PPC_REG_3)]


def gather_reference(dol_bytes, requested_ids, sections):
    """Original normal-mode802BACA4 request insertion, including absent-ID skips."""
    from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
    from unicorn import ppc_const as reg
    if hashlib.sha256(dol_bytes).hexdigest()!=DOL_SHA256 or len(sections)>1024 or len(requested_ids)>512:
        raise ValueError('Invalid original request-gather inputs')
    image=DolImage(dol_bytes)
    machine=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
    for base,size in ((0x802B9000,0x1000),(0x802BA000,0x1000)):
        machine.mem_map(base,size);machine.mem_write(base,image.read(base,size))
    machine.mem_map(0x80410000,0x20000)
    machine.mem_map(0x10000000,0x80000)
    manager,table,requests=0x10000000,0x10010000,0x10006000
    machine.mem_write(manager,struct.pack('>II',table,len(sections)))
    machine.mem_write(manager+0x868,struct.pack('>I',0x10005000))
    machine.mem_write(requests,struct.pack(f'>{len(requested_ids)}h',*requested_ids))
    for i,section in enumerate(sections):
        machine.mem_write(table+i*92+8,struct.pack('>h',section['id']))
        machine.mem_write(table+i*92+24,struct.pack('>I',section['bytes']))
    for r,value in ((1,0x1007E000),(3,manager),(4,requests),(5,len(requested_ids)),(6,0)):
        machine.reg_write(getattr(reg,f'UC_PPC_REG_{r}'),value)
    machine.reg_write(reg.UC_PPC_REG_LR,0x1007F000)
    state={'stopped':False}
    def hook(uc,address,size,_):
        if address==0x1007F000:
            state['stopped']=True;uc.emu_stop()
        elif not (0x802BACA4<=address<0x802BADCC or 0x802B90C4<=address<0x802B9108):
            raise ValueError(f'Original gather escaped bounded call graph: {address:08x}')
    machine.hook_add(UC_HOOK_CODE,hook)
    machine.emu_start(0x802BACA4,0x1007F004,count=2000000)
    if not state['stopped']:
        raise ValueError('Original gather instruction budget exceeded')
    count=struct.unpack('>I',machine.mem_read(manager+0x2DC,4))[0]
    if count>len(sections):
        raise ValueError('Original gather output exceeds source section table')
    result=[]
    for i in range(count):
        pointer=struct.unpack('>I',machine.mem_read(manager+0x2E0+i*4,4))[0]
        if not table<=pointer<table+len(sections)*92 or (pointer-table)%92:
            raise ValueError('Original gather produced invalid section pointer')
        result.append(struct.unpack('>h',machine.mem_read(pointer+8,2))[0])
    return result
