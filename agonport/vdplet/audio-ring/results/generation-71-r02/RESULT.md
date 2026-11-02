# Generation 71 Wolf host-ring observation

The one selected `r02` invocation completed and qualified. Startup, structural
gameplay readiness, observer-window overlap, finalization, reader validation,
normal application exit, and cleanup all passed. The runner exited after
103.295 seconds without forced cleanup. Fresh whole-host inspections were empty
at checkout and release; the FIFO had no next request when released.

The ten-second observer window contained 4,435 metadata records and 163,840
real dequeued samples at the nominal 16,384 Hz. It recorded no `0x7f` fill
samples, no dropped samples, no capacity hit, and no arithmetic error. Ring
depth remained between 5,065 and 5,543 samples in the recorded events, with a
maximum of 5,543 samples (0.338318 nominal seconds).

Of the dequeued samples, 158,563 had known enqueue and dequeue times. For those
fully observed samples, the reader gives a weighted mean residence bound of
325.774095–325.774559 ms. Another 5,277 dequeues were left-censored at the
window entrance and 5,277 samples remained right-censored at its end; their
ages remain unknown and are not represented by that known-sample mean. Observed
residence lower/upper extrema were 307.530927 ms and 337.297282 ms.

This establishes a large, stable delay inside the host extracted-U8
enqueue-to-real-dequeue ring boundary. It does not identify the injected Space
pair with a particular sample and cannot measure or assign command admission,
parser, mixer, PulseAudio server/device, DAC, speaker, or total audible latency.
The Oryx host was not quiet: a four-thread SU2 scientific job was active and
load average was approximately 4.4–4.8. This was a functional observation, not
a benchmark or causal comparison.

`SHA256SUMS` pins the retrieved raw run, observer, UART, traffic, capture, and
host-context records. It intentionally does not hash itself or this derived
summary.
