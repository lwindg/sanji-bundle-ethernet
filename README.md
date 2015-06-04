# sanji-ethernet
Ethernet model.

## Usage

### Release a New Version
Both `debian/changelog` and `bundle.json` will be updated by new version.

```
make release [DIST=] [VER=]
```

arguments:
 - [DIST]     optional; default is unstable
 - [VER]      optional; the version will be increased automatically by default

### Build Debian Package
```
make deb [SANJI_VER=]
```

arguments:
 - [SANJI_VER]  optional; sanji's version, default to 1.0

