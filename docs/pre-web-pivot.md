# Pre-web-pivot preservation — September 24, 2026

This checkpoint preserves the completed Python card-data layer, Qt reference client,
MCP adapter, tests, and documentation before the approved web pivot.

Last regression run: 82 passed in 14.81 seconds. Windows default pytest temporary
folder permissions required an explicit workspace --basetemp directory.
The packaged Qt executable fails importing QtCore with a DLL procedure-not-found
error. Source-client validation does not certify the packaged executable.
This is a preserved prototype, NOT a certified desktop release.

Synchronized databases, credentials, personal profiles, environments, images and
executables are excluded from Git. The existing card database remains locally
available; a separate SQLite backup is retained in the task preservation folder.
