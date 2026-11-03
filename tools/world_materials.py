"""Apply the observed GC world texture's opacity state, preserving source RGB.

Speed.dol 0x801066D8 reads TextureInfo bytes 85 (alpha test enabled iff 1)
and 86 (blend mode). Mode 0 disables blending and enables depth writes;
mode 1 uses SRCALPHA/INVSRCALPHA and mode 2 uses SRCALPHA/ONE; both disable depth writes. An image's alpha
histogram alone cannot determine whether a wall should be transparent.
Other blend modes need explicit runtime support before world conversion.
"""


def world_rgba(texture):
    alpha_test = texture['alpha_test_mode'] == 1
    blend = texture['blend_mode']
    if blend not in (0, 1, 2):
        raise ValueError(f'Unsupported world blend mode {blend}')
    rgba = texture['rgba']
    if blend == 0 and not alpha_test:
        result = bytearray(rgba)
        result[3::4] = bytes([255]) * (len(result) // 4)
        return bytes(result), 'opaque: original blending and alpha test disabled'
    if blend == 2:
        return rgba, 'source alpha: original additive SRCALPHA/ONE blending'
    return rgba, 'source alpha: original blending or alpha test enabled'
