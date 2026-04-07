# Changelog

All notable changes to this project are documented in this file.

## [0.6.0](https://github.com/leahana/m2c-pipeline/compare/v0.5.1...v0.6.0) (2026-04-07)


### Features

* **cli:** require Python 3.11+ at runtime ([7901b2e](https://github.com/leahana/m2c-pipeline/commit/7901b2e0f3f242cf5bdaeb3b6e8124c32fea14a3))
* **dev:** add timestamped local preview packager ([f549c1a](https://github.com/leahana/m2c-pipeline/commit/f549c1a9ec28d7f08c62486dcc9212e42252669d))
* runtime guard, Chiikawa cast, auth runbook, CC Switch contract, preview packager ([b358fc7](https://github.com/leahana/m2c-pipeline/commit/b358fc7d8d40897a1e4b7f9dae9a5aceee9c6fee))
* **translator:** enforce distinct Chiikawa cast for simple linear flows ([da231b6](https://github.com/leahana/m2c-pipeline/commit/da231b6ba1bcd6c491c5b11d6f267d9c67113cc8))


### Documentation

* **cc-switch:** document remote install contract and add CI guard ([ca89912](https://github.com/leahana/m2c-pipeline/commit/ca8991262db8ba55ad4d5c76e146ee623d421cd4))
* **skill:** add credential readiness phase and vertex auth runbook ([8810dfb](https://github.com/leahana/m2c-pipeline/commit/8810dfbb02807df44479c8a5cc50991a642e6043))

## [0.5.1](https://github.com/leahana/m2c-pipeline/compare/v0.5.0...v0.5.1) (2026-04-05)


### Documentation

* expand skill runtime guidance and eval coverage ([2776482](https://github.com/leahana/m2c-pipeline/commit/277648227d93b209ce48aba0e1511b9c0d0aeb8b))
* expand skill runtime guidance and eval coverage ([4a7f00c](https://github.com/leahana/m2c-pipeline/commit/4a7f00ca25f2791dfc78a3e0efe8af0bcc98d266))

## [0.5.0](https://github.com/leahana/m2c-pipeline/compare/v0.4.1...v0.5.0) (2026-04-05)


### Features

* add python preflight bootstrap flow for skill runtime ([e87be53](https://github.com/leahana/m2c-pipeline/commit/e87be53b7c33b55eec23727927bf278866f8b52f))
* harden skill bootstrap and published artifact validation ([b041452](https://github.com/leahana/m2c-pipeline/commit/b041452744a171cabce12fad6476297f3a530037))

## [0.4.1](https://github.com/leahana/m2c-pipeline/compare/v0.4.0...v0.4.1) (2026-04-05)


### Bug Fixes

* preserve skill branch readme layout ([d66a6a7](https://github.com/leahana/m2c-pipeline/commit/d66a6a7513bddb772ef863b7f2f9569f67325d0d))
* preserve skill branch readme layout ([eb02aa4](https://github.com/leahana/m2c-pipeline/commit/eb02aa4686ba052275c6355498d42f9213b821c6))

## [0.4.0](https://github.com/leahana/m2c-pipeline/compare/v0.3.1...v0.4.0) (2026-04-05)


### Features

* add SKILL_README.md as skill-branch README ([d8a6274](https://github.com/leahana/m2c-pipeline/commit/d8a627422b302163531be31958334269da2e31c8))
* add SKILL_README.md as skill-branch README ([0e91c52](https://github.com/leahana/m2c-pipeline/commit/0e91c5292170a87564a7859e989ce8a8c85b9ba3))

## [0.3.1](https://github.com/leahana/m2c-pipeline/compare/v0.3.0...v0.3.1) (2026-04-05)


### Bug Fixes

* pass auth token to publish_skill_branch for CI push ([83c3921](https://github.com/leahana/m2c-pipeline/commit/83c39213f011f85d6bfc1ad963c778d3739847a9))
* pass auth token to publish_skill_branch via SKILL_PUBLISH_TOKEN env ([6775666](https://github.com/leahana/m2c-pipeline/commit/67756667e36eb00479c90eaaddf0247a490a65bc))

## [0.3.0](https://github.com/leahana/m2c-pipeline/compare/v0.2.1...v0.3.0) (2026-04-05)


### Features

* publish skill-only content to skill branch on release ([0b7f7f4](https://github.com/leahana/m2c-pipeline/commit/0b7f7f4a45b8eac6d6fcb00a55acd9741d162e5e))
* publish skill-only content to skill branch on release ([dccb814](https://github.com/leahana/m2c-pipeline/commit/dccb814796ad8a52fbe3e3caedcc164f2b35aaa9))

## [0.2.1](https://github.com/leahana/m2c-pipeline/compare/v0.2.0...v0.2.1) (2026-04-04)


### Bug Fixes

* make workflow permission validation order-insensitive ([80d63ff](https://github.com/leahana/m2c-pipeline/commit/80d63ff32f2d7379551b697e7fedced9551ea327))
* migrate release workflow to release-please ([8b07ce9](https://github.com/leahana/m2c-pipeline/commit/8b07ce9a79e9ffad5b3814ade0ac90b9742d3089))


### Documentation

* update README for v0.2.0 — project tree, character assignment, test list ([268bd9f](https://github.com/leahana/m2c-pipeline/commit/268bd9f522cffd3c7c46cfdbb5c5c8a37fd2a9e3))

## [0.2.0] - 2026-04-04

### Added

- Anthropic skill spec docs, eval fixtures, and reference material for the public `m2c_pipeline` skill.
- Character assignment guidance in Mermaid-to-Chiikawa prompt translation.

### Changed

- Repository policy, README, and CI documentation for the v0.2.0 release line.
- GitHub automation coverage with Claude review support and stricter release governance checks.
