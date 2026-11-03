"""Explicit count-statistic diagnostics after original-emitter parity was proved.

Uses the reviewed opt-in decoder API. Its default stays strict, original source
bytes are never patched, and all consumed geometry constraints remain mandatory.
"""

from decode_world import decode_model


def diagnose_model(data, start, end):
    model=decode_model(data,start,end,allow_triangle_statistic_mismatch=True)
    if not model['triangle_statistic_mismatch']:
        return model,None
    return model,dict(declared_triangles=model['declared_triangles'],
                      emitted_position_index_triangles=model['emitted_position_index_triangles'],
                      note='Original header retained as a statistic discrepancy; all consumed geometry checks passed')
