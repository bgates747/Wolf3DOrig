# Generation 75 corrected startup-ring observation

The one selected startup invocation completed and qualified. Startup, structural
gameplay readiness, actual SETUP+0..10-second observer data, initial-history
witness, finalization, reader validation, expected shot non-overlap, normal
application exit, and cleanup all passed. The runner exited after 103.473
seconds without forced cleanup. Fresh whole-host inspections were empty at
checkout and release; the FIFO had no next request when released.

The first saved record was a dequeue request with `produced_before=0` and
`before=0`, proving no unobserved pre-window production or queued depth at the
corrected observer's SETUP origin. First production occurred 0.486777 seconds
after SETUP and the first real dequeue occurred at 0.488278 seconds. The real
Space write at runner T0+92 seconds did not overlap the startup window, as
required.

The ten-second window contained 4,089 metadata records. Producers supplied
156,032 real samples; 155,702 were dequeued and 330 remained pending at the
right edge. There were no left-censored samples or drops. The host supplied
8,171 `0x7f` fill samples across 85 dequeue events while the ring lacked enough
real data; the last such event occurred 8.179330 seconds after SETUP. These
fills document host-ring underflow and must not be interpreted as proof of
audible silence.

For the 155,702 fully observed real samples, weighted mean enqueue-to-dequeue
residence was bounded to 19.286677–19.287097 ms. Observed residence lower/upper
extrema were 0.235087 ms and 32.066861 ms. Maximum observed depth was 529
samples (0.032288 nominal seconds), and the ring ended the window at 330
samples. Thus the roughly 5K-sample/325 ms bank seen in the separately limited
generation-71 late-window run was not present during this run's first ten setup
seconds. The two runs are not a matched pristine-baseline comparison, and this
observation cannot locate or explain any backlog formation after ten seconds.

This remains a host extracted-U8 ring measurement only. It does not identify a
shot sample or measure command admission, parser, mixer, PulseAudio/device,
DAC, speaker, or total audible latency. Host load average was about 1.01 before
and 2.39 after; the saved process records show ordinary desktop activity and no
concurrent SU2 scientific job. This is functional evidence, not a performance
benchmark.

`SHA256SUMS` pins the retrieved raw run, observer, UART, traffic, capture,
custody, and host-context records. It intentionally does not hash itself or
this derived summary.
