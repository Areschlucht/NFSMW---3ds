# Indexed-world integration review

No blocking correctness defect was found in the reviewed candidate. Existing production ASan/UBSan tests reconstruct all112,077 original ordered corners and1,046 material batches exactly.

The independent `index_failures.c` harness injects each of the encoder's three allocation failures and constructs96 distinct inputs colliding in the same FNV bucket to trigger the real probe-budget fallback. Every failure leaves empty output and all tracked allocations balanced; ASan/UBSan passes.

The candidate is compile-gated, retains expanded fallback, stores unique vertices and u16 indices in one128-byte-aligned linear block, zeroes padding, and flushes the full allocation. Draw counts/first values remain offsets into the original corner/index stream. CPU temporary allocations are freed after copying; only the GPU block owns the interior index pointer.

The hardware specialist confirmed from pinned SDK ARM code that DrawElements clears GPU_VERTEX_OFFSET0x022A before drawing and restarts primitive assembly. Thus alternating unindexed car draws with indexed world draws does not retain the car's nonzero first offset. Current maxindex50,175 and maxdrawcount10,707 avoid u16/count extremes.

Remaining validation is hardware-specific: cache reuse, timing, actual u16 boundary semantics, and real GPU execution. No FPS or 1:1 fidelity conclusion follows from this native review. See review.json for source hashes and detail.
