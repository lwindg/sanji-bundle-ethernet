# sanji-ethernet

This bundle handle the ethernet interfaces.

## Usage

### Release the Source Package
The version is located in `bundle.json`.

```
make archive
```

### Build Debian Package
```
make -C build-deb
```

### Commit Changes
Whenever a set of changes are ready to be committed, you should:

1. Update `version` in `bundle.json`.
2. Use `make -C build-deb changelog` to add change-logs.

