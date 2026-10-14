# NBDC-0002 media preparation and next evaluation gate

The existing canonical NBDC Case Register controls case maturity. The governing
Naturalistic Behavioral Deciphering Benchmark protocol controls the blind sequence.
`contracts/nbdc0002_media_preparation_receipt.json` records this preparation pass;
it is not a new benchmark schema or scored run. Run History remains empty.

The exact publisher WebM was downloaded from the register's
[Commons source](https://commons.wikimedia.org/wiki/File:Domestic_catfight.webm).
It matches 135,150,326 bytes and registered SHA-1
`0cf77811f2e5e9d304b9a632185ed603971fcd88`; independently calculated SHA-256 is
`b6925f989d8a3d11cc74268de43ff5552a5d1125481c2da3294de6c9dd568ff8`.
Creator Panini!, source date 2024-02-21 and source-specific CC0 rights are retained.
This is the publisher's encoded WebM, not an asserted untouched camera original.

All source video/audio bytes decoded without an error using FFmpeg 7.1. Two
neutral-named MP4 playback candidates were generated at full resolution/duration:
H.264 CRF18, preset fast, yuv420p, no cropping/rescaling/frame-rate change; global
and stream metadata and chapters removed; either AAC 192k natural audio or no
audio. Both derivatives fully decode to 1,146 video frames. The receipt contains
their independent hashes, byte sizes, channels and canonical Drive identities.
These are lossy playback derivatives, not source-equivalent bytes. They are stored
in the existing 04.3 Derived Features folder. The original upload was rejected
before invocation by the connector's 104,857,600-byte input limit; the exact source
is retained locally and checksum-pinned at its public source URL, not archived in
Drive. Do not claim otherwise or duplicate/chunk it into a substitute raw master.

The acquisition can be repeated on a local or remote runtime without credentials:

```bash
mkdir -p build/nbdc/NBDC-0002
curl --fail --location --output build/nbdc/NBDC-0002/source.webm \
  https://upload.wikimedia.org/wikipedia/commons/b/b0/Domestic_catfight.webm
python - <<'PY'
from pathlib import Path
import hashlib
p = Path('build/nbdc/NBDC-0002/source.webm')
assert p.stat().st_size == 135150326
assert hashlib.sha1(p.read_bytes()).hexdigest() == '0cf77811f2e5e9d304b9a632185ed603971fcd88'
assert hashlib.sha256(p.read_bytes()).hexdigest() == 'b6925f989d8a3d11cc74268de43ff5552a5d1125481c2da3294de6c9dd568ff8'
PY
```

With FFmpeg 7.1 available, the recorded transformation is:

```bash
ffmpeg -nostdin -i build/nbdc/NBDC-0002/source.webm -map 0:v:0 \
  -map_metadata -1 -map_metadata:s -1 -map_chapters -1 \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -movflags +faststart \
  -an build/nbdc/NBDC-0002/NBDC-0002_video_only.mp4
```

For the natural-audio candidate replace `-an` with `-map 0:a:0 -c:a aac -b:a 192k`.
Record a new derivative hash for a different FFmpeg build; do not promise identical
encoding bytes across builds. Never overwrite the pinned source or a frozen case.

Only a sampled technical contact sheet was visually inspected. This does not
certify behavioral observations or an exhaustive framing audit. The preparer has
seen the source title/description and full-clip samples and is **exposed**. No blind
analysis, predictions, scoring, contamination challenge or adjudication ran.
Source captions and the filename's framing remain contextual claims only.

Next: an exposure-clean reviewer/session must receive only approved neutral
sensory materials, with an exposure attestation and checks for embedded framing.
Fix admissible channels, clip bounds, the prospective prediction cut and scoring
before execution. Freeze observations, competing hypotheses and predictions
before revealing source context or withheld continuation; retain that output;
then perform the framed contamination challenge and adjudication. Natural audio
is not speech-masked; assess cueing before admitting it. The case remains CANDIDATE
with evaluation held, and cannot be called CURATED, BENCHMARK_READY or FROZEN until
the corresponding protocol gates actually pass. No semantic truth label is created.
