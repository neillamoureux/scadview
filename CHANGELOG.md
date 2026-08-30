# Changelog

## [0.2.9](https://github.com/neillamoureux/scadview/compare/v0.2.8...v0.2.9) (2026-08-30)


### Features

* add feature-level debug visualization ([#160](https://github.com/neillamoureux/scadview/issues/160)) ([8e2c3c4](https://github.com/neillamoureux/scadview/commit/8e2c3c46b9681419cdcd5dde3887b98bb13d13d9))


### Documentation

* document agent contribution workflow ([#159](https://github.com/neillamoureux/scadview/issues/159)) ([5a8bb88](https://github.com/neillamoureux/scadview/commit/5a8bb88863baa9093b85da36ee334aa4729dabe7))


### Chores

* Add OpenSpec support ([#157](https://github.com/neillamoureux/scadview/issues/157)) ([550295a](https://github.com/neillamoureux/scadview/commit/550295a803c9d9c7f5d387f64b92d4804df452f3))

## [0.2.8](https://github.com/neillamoureux/scadview/compare/v0.2.7...v0.2.8) (2026-05-31)


### Features

* add toggleable mesh features ([#146](https://github.com/neillamoureux/scadview/issues/146)) ([dbb8df5](https://github.com/neillamoureux/scadview/commit/dbb8df5b7a87e8cb0aafb46cdae91f7af64f6877))
* Automate docs screenshots with manifest tooling ([#150](https://github.com/neillamoureux/scadview/issues/150)) ([d5905c0](https://github.com/neillamoureux/scadview/commit/d5905c04f79365cb18cb3fe22ce066a460a941e9))


### Bug Fixes

* **ci:** remove PAT dependency from release-please flow ([#152](https://github.com/neillamoureux/scadview/issues/152)) ([8602202](https://github.com/neillamoureux/scadview/commit/8602202a9c1f9a9e7e215fbb967cce7abf89c5a4))


### Chores

* replaced pyright with py ([#144](https://github.com/neillamoureux/scadview/issues/144)) ([011ec57](https://github.com/neillamoureux/scadview/commit/011ec5732b85f01d655b33dfa5aded91ecde6afa))
* Update AGENTS.md and add .codex/config.toml for codex agent ([#142](https://github.com/neillamoureux/scadview/issues/142)) ([c0cc678](https://github.com/neillamoureux/scadview/commit/c0cc678f00ae0ba44811b5ea990f826cc4a23fb6))

## [0.2.7](https://github.com/neillamoureux/scadview/compare/v0.2.6...v0.2.7) (2026-03-09)


### Bug Fixes

* reject non-finite mesh inputs during load ([#138](https://github.com/neillamoureux/scadview/issues/138)) ([9918b1c](https://github.com/neillamoureux/scadview/commit/9918b1c210741e013e67efa56049cd66ae25abb2))


### Chores

* Update github actioms to build and publish on release ([#128](https://github.com/neillamoureux/scadview/issues/128)) ([f31998b](https://github.com/neillamoureux/scadview/commit/f31998b22b0e3710f5cae6c9ac6efe639f849a9d))

## [0.2.6](https://github.com/neillamoureux/scadview/compare/v0.2.5...v0.2.6) (2026-02-15)


### Features

* Diagnostic information is logged to the subdirectory of where scadview is run from, ./.scadview/debug_info.json. ([1addc98](https://github.com/neillamoureux/scadview/commit/1addc98e7ddacdd9a1665172ea8f440ac3398213))


### Bug Fixes

* Update pixel scale factor to correct cam moves when scale changes ([#126](https://github.com/neillamoureux/scadview/issues/126)) ([13215d6](https://github.com/neillamoureux/scadview/commit/13215d657a29444bf57ee0b990b1bd575e882f9e))
* When resizing the gl viewport, use scaled device coordinates to set the logical viewport size ([#121](https://github.com/neillamoureux/scadview/issues/121)) ([1590902](https://github.com/neillamoureux/scadview/commit/1590902bad6346a507f374c12b802df76768e5fe))


### Documentation

* Add heart vase and spice rack examples ([#116](https://github.com/neillamoureux/scadview/issues/116)) ([b0cf656](https://github.com/neillamoureux/scadview/commit/b0cf656a7ecdf184779368cd25c27a37ea6133f8))


### Chores

* Enable versioned docs using mike ([#123](https://github.com/neillamoureux/scadview/issues/123)) ([23e6969](https://github.com/neillamoureux/scadview/commit/23e69698507ecdfafb9b59a8cd8b6861f398e78f))

## [0.2.5](https://github.com/neillamoureux/scadview/compare/v0.2.4...v0.2.5) (2026-02-07)


### Features

* Automatically set color and alpha in debug mode ([6a5470c](https://github.com/neillamoureux/scadview/commit/6a5470cb37597d0d44f9b40c858af09815b09a61))


### Documentation

* Remove color setting in examples/cube_minus_sphere.py; update image for docs, and fix text in docs. ([6a5470c](https://github.com/neillamoureux/scadview/commit/6a5470cb37597d0d44f9b40c858af09815b09a61))
* Update tutorial for change in debug mode feature. ([6a5470c](https://github.com/neillamoureux/scadview/commit/6a5470cb37597d0d44f9b40c858af09815b09a61))


### Tests

* Add test for automated setting of colors in debug mode. ([6a5470c](https://github.com/neillamoureux/scadview/commit/6a5470cb37597d0d44f9b40c858af09815b09a61))

## [0.2.4](https://github.com/neillamoureux/scadview/compare/v0.2.3...v0.2.4) (2026-02-06)


### Bug Fixes

* Set upper limit for python &lt;3.14 ([#108](https://github.com/neillamoureux/scadview/issues/108)) ([d290e70](https://github.com/neillamoureux/scadview/commit/d290e70256704da375931e81a6b963d5d3e52f06))


### Documentation

* Add Python limit to other docs ([#110](https://github.com/neillamoureux/scadview/issues/110)) ([e8cd6c5](https://github.com/neillamoureux/scadview/commit/e8cd6c5f8f1626aaa486bb4a93d306b1af802fa7))

## [0.2.3](https://github.com/neillamoureux/scadview/compare/v0.2.2...v0.2.3) (2026-02-02)


### Documentation

* Add project.urls in pyproject.toml ([#106](https://github.com/neillamoureux/scadview/issues/106)) ([72c1269](https://github.com/neillamoureux/scadview/commit/72c1269942428f68088a6678f4f7884c9ccd9327))


### CI

* Add github action to publish to github pages ([#103](https://github.com/neillamoureux/scadview/issues/103)) ([cc47ac9](https://github.com/neillamoureux/scadview/commit/cc47ac9ab6f35a3cb17a9516a714bfc30295e406))

## [0.2.2](https://github.com/neillamoureux/scadview/compare/v0.2.1...v0.2.2) (2026-02-01)


### Documentation

* Replace development instructions with install and getting started in README ([#100](https://github.com/neillamoureux/scadview/issues/100)) ([2d487a5](https://github.com/neillamoureux/scadview/commit/2d487a596c41f3c197dc8f1f4a24563406a87769))

## [0.2.1](https://github.com/neillamoureux/scadview/compare/v0.2.0...v0.2.1) (2026-02-01)


### Features

* Add title and wait message to the splash screen ([#63](https://github.com/neillamoureux/scadview/issues/63)) ([5b6d018](https://github.com/neillamoureux/scadview/commit/5b6d018a72883d5237e94f5a6b7be6b9700f0835))
* Adjust logging so that the loaded module can write logs to the console and set the logging level for itself ([#68](https://github.com/neillamoureux/scadview/issues/68)) ([9c38d53](https://github.com/neillamoureux/scadview/commit/9c38d539e6ea0babf8beee589e482ad6fb3c6dcf))
* automate make help messages ([#81](https://github.com/neillamoureux/scadview/issues/81)) ([2de93e3](https://github.com/neillamoureux/scadview/commit/2de93e384ce2d5fb1f7cc4f5aa0d91c500fc0323))
* Do not try to use tkinter and show splash if tkinter not available ([#65](https://github.com/neillamoureux/scadview/issues/65)) ([449b503](https://github.com/neillamoureux/scadview/commit/449b5038906f69e9a7954baca774862a52632d05))
* queue log messages from subprocesses ([#67](https://github.com/neillamoureux/scadview/issues/67)) ([65ec935](https://github.com/neillamoureux/scadview/commit/65ec935185ca85d762167249719068fe75261544))


### Bug Fixes

* Add Resolves #__ for issue link to auto-close the issue ([#90](https://github.com/neillamoureux/scadview/issues/90)) ([5b01de2](https://github.com/neillamoureux/scadview/commit/5b01de2c33baf814de4aeb01078479c0c4c0b9ef))
* When loading the mesh code, place its path at the front of sys.path ([#91](https://github.com/neillamoureux/scadview/issues/91)) ([c78f7c7](https://github.com/neillamoureux/scadview/commit/c78f7c7faed9efe3febe08c8e5f2c85afc66941d))


### Documentation

* Add CODE_OF_CONDUCT.md ([#96](https://github.com/neillamoureux/scadview/issues/96)) ([8ed8181](https://github.com/neillamoureux/scadview/commit/8ed8181936ef70b1bbd0731a64db484845f5b095))
* Update CONTRIBUTING.md to list commit types for commit messages ([3038ce7](https://github.com/neillamoureux/scadview/commit/3038ce7988ba8e0ff508cfa5e780f8f0b87811b7))
* Update CONTRIBUTING.md with a more complete description. ([#94](https://github.com/neillamoureux/scadview/issues/94)) ([8030909](https://github.com/neillamoureux/scadview/commit/80309091455349d07dff092fcd2a2f5e7690b6d4))


### CI

* Add Release Please ([#92](https://github.com/neillamoureux/scadview/issues/92)) ([3038ce7](https://github.com/neillamoureux/scadview/commit/3038ce7988ba8e0ff508cfa5e780f8f0b87811b7))
* Add release-please config, manifest, and workflow ([3038ce7](https://github.com/neillamoureux/scadview/commit/3038ce7988ba8e0ff508cfa5e780f8f0b87811b7))


### Chores

* Add LICENSE, CONTRIUTING.md and update README.md ([#61](https://github.com/neillamoureux/scadview/issues/61)) ([4858d7a](https://github.com/neillamoureux/scadview/commit/4858d7ac99d73a3aa36488078f8d90929e112083))
* Add PyPI test index to pyproject.toml to enable test releases ([#98](https://github.com/neillamoureux/scadview/issues/98)) ([88ba9eb](https://github.com/neillamoureux/scadview/commit/88ba9eb00abda173bb3e453183ee0c1616091c4e))
* splash code clean up ([#66](https://github.com/neillamoureux/scadview/issues/66)) ([7cf6295](https://github.com/neillamoureux/scadview/commit/7cf629592bb5de2c16c1a1b2966ea222234e7067))
* update docs ([#70](https://github.com/neillamoureux/scadview/issues/70)) ([ce634a2](https://github.com/neillamoureux/scadview/commit/ce634a28d6d48f12e0b19eeda54cb4e6b5b91da0))
* update templates to be less noisy when complete ([#86](https://github.com/neillamoureux/scadview/issues/86)) ([20b4e33](https://github.com/neillamoureux/scadview/commit/20b4e33bb4c8704a9b1ac07ee3154aaf29e4936d))
