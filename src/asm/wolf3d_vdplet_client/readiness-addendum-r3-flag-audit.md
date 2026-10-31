# Production-client r3 failure-flag audit addendum

Golem accepted the exact handle/carry diagnosis and requested inspection of the
adjacent `cp W3D_VDPLET_STATUS_RUNTIME; ret nz` path before final readiness.

That path is reached only after `w3d_vdplet_wait_reply` returned carry set.
Its only reachable non-runtime statuses are timeout 1 and protocol 2. Both are
strictly below runtime 3, so `cp W3D_VDPLET_STATUS_RUNTIME` leaves carry set
before the existing `ret nz`. Incompatible, file, package and token statuses
are produced by callers outside this reply-wait/unload path and cannot reach
this comparison.

The source audit therefore confirms that the adjacent path does not reproduce
the generation-33 carry loss. Per Golem's reconciliation, it remains unchanged;
the final code correction is limited to the two proven defects: store the
original handle high byte before the nonzero test, and explicitly set carry
when close retains a live handle. No target request is authorized by this
addendum.
