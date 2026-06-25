# Third-Party Licenses

This document lists third-party software and assets used by MediaSeg.

---

## PySide6 (Qt for Python)

Project:
https://wiki.qt.io/Qt_for_Python

License:
LGPL v3

Official License:
https://www.gnu.org/licenses/lgpl-3.0.html

Used for:
Desktop GUI framework.

---

## FFmpeg & FFprobe

Project:
https://ffmpeg.org/

License:
FFmpeg is LGPL v2.1 or later by default.

FFmpeg legal checklist:
https://ffmpeg.org/legal.html

LGPL v2.1 text:
https://www.gnu.org/licenses/old-licenses/lgpl-2.1.html

Used for:
Media inspection and media splitting operations.

Notes:

- MediaSeg release builds bundle FFmpeg and FFprobe.
- The bundled FFmpeg build must not include `--enable-gpl` or `--enable-nonfree`.
- The bundled FFmpeg build is produced from official FFmpeg source with dynamic libraries enabled.
- Matching FFmpeg source and build-configuration files are distributed alongside MediaSeg release artifacts.
- Public download pages for MediaSeg releases should keep the matching FFmpeg source archive on the same download page as the binary artifacts.
- Source runs of MediaSeg can still use local `ffmpeg` and `ffprobe` from `PATH`.

---

## Lucide Icons

Project:
https://lucide.dev/

License:
ISC License

Used for:
SVG interface icons used throughout the application.

ISC License

Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT). All other portions are Copyright (c) 2022-2024 by Lucide Contributors.

Permission to use, copy, modify, and/or distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
