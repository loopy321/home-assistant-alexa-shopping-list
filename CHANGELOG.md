# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

<!-- RELEASE START -->
## [2602.054.00] - 2026-02-23

### Improvements
- **Added diagnostic logging on Selenium timeout** — Captures screenshot, current URL, and page source snippet when `TimeoutException` occurs, aiding in debugging headless browser issues
<!-- RELEASE END -->

## [2602.050.01] - 2026-02-19

### CI/CD
- **Fixed HASS addon publish step** — `git commit` no longer fails when version is already up to date

## [2602.050.00] - 2026-02-19

### Critical Fixes
- **Fixed `_do_sync()` crash** — `loop` variable was defined in `sync()` but never passed to `_do_sync()`, causing `NameError` and breaking shopping list synchronization
- **Fixed `UnboundLocalError` in `sync()`** — `result` variable was not initialized before the `try/except` block, causing the "result" missing error in the custom component

### Bug Fixes
- **Protected cache from data loss** — `_update_cached_list()` now rejects `None` and empty lists when cache already contains data
- **Added exception handling to all server commands** — Selenium operations wrapped in `try/except/finally`, ensuring browser cleanup on errors
- **Re-enabled exception handling in WebSocket handler** — Catches `JSONDecodeError` and general exceptions gracefully
- **Fixed `_set_config_value` crash** — No longer throws `KeyError` on non-existent config keys
- **Fixed `_route_command` missing returns** — `shutdown` and unknown commands now return proper responses
- **Removed reference to undefined `_cmd_mfa`** — Dead code cleaned up
- **Used `clients.discard()` instead of `clients.remove()`** — Prevents `KeyError` during WebSocket cleanup
- **Replaced `_is_syncing` boolean with `asyncio.Lock()`** — Prevents race conditions in concurrent sync

### Improvements
- **Robust virtual list scrolling** — Handles `StaleElementReferenceException`, compares by text instead of WebElement references, max 50 scroll limit
- **Flexible URL matching** — Uses `in` operator instead of exact `==` for Alexa shopping list URL
- **Unique item IDs** — Generated via MD5 hash instead of space-to-underscore replacement
- **Added proper logging** — Server uses Python `logging` module for error reporting

### CI/CD
- **Tag-based releases** — Workflow only triggers on version tags, not every push to main
- **Updated Docker Hub and addon repo references**
- **Added `workflow_dispatch` trigger** — Allows manual workflow runs from GitHub UI
<!-- RELEASE END -->

## [2602.050.00] - 2026-02-19

First release from raidolo fork.
