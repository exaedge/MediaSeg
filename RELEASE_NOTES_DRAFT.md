# MediaSeg v0.9.0 - Initial Public Release

MediaSeg is a local macOS utility that splits large media files into upload-ready chunks while preserving quality.

It was originally created to prepare long recordings for NotebookLM uploads, and can also be used for other size-limited media upload workflows.

This release includes:

- PySide6 desktop GUI
- MP4 splitting by target size
- WEBM input support via MP4 conversion
- Custom output folder support
- Activity Indicator with status icons
- Output folder isolation for temporary WEBM conversion files
- Automatic cleanup for normal completion and handled error paths
- PyInstaller macOS app packaging
- Third-party license documentation

Known limitations:

- WEBM conversion can take longer than MP4 processing.
- CPU usage may be higher during WEBM conversion.
- Force-quitting the app during conversion may leave temporary files inside the output folder.
- Very long filenames or unusually tall windows may still expose layout issues in some views.
