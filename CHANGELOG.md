# Changelog

## [0.1.4](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.3...ha-weewx-v0.1.4) (2026-05-27)


### Features

* cache robots.txt flat for 24h ([#29](https://github.com/bakerkj/ha-weewx/issues/29)) ([e644e17](https://github.com/bakerkj/ha-weewx/commit/e644e176aa35df9608083174af2781b8c168d429))
* per-period mtime cache tiers + /config override ([#25](https://github.com/bakerkj/ha-weewx/issues/25)) ([3e53544](https://github.com/bakerkj/ha-weewx/commit/3e535441c90529f5635fff1cca9d0ccaae75d8fe))
* per-request NOAA cache via njs (current vs. immutable) ([#28](https://github.com/bakerkj/ha-weewx/issues/28)) ([3fd16dd](https://github.com/bakerkj/ha-weewx/commit/3fd16dd990f6bb5aac53a4cd1c77ed3e6872c7a0))


### Documentation

* fix year-plot cache example (24h, not 7d) ([#27](https://github.com/bakerkj/ha-weewx/issues/27)) ([ef52bef](https://github.com/bakerkj/ha-weewx/commit/ef52bef7f3a821d92a7fbb757ce7ad6dd76a7a7e))


### Tests

* behavioral test for the nginx cache layer ([#30](https://github.com/bakerkj/ha-weewx/issues/30)) ([d5980c9](https://github.com/bakerkj/ha-weewx/commit/d5980c9fdaa8cffb9be1758b76ef6fe124ac21d2))


### Build System

* quiet weectl's INFO banner during image build ([#31](https://github.com/bakerkj/ha-weewx/issues/31)) ([f90b5e0](https://github.com/bakerkj/ha-weewx/commit/f90b5e0a9522a30b80986d6228bfc664c4f25d26))

## [0.1.3](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.2...ha-weewx-v0.1.3) (2026-05-26)


### Features

* report cache headers + brotli/gzip compression in nginx ([#22](https://github.com/bakerkj/ha-weewx/issues/22)) ([8604ad2](https://github.com/bakerkj/ha-weewx/commit/8604ad2b95e18dc5f6865584d0d0afdc2c4b75e0))


### Bug Fixes

* guard rtgd start_of_day_reset against missing manifest obs ([#23](https://github.com/bakerkj/ha-weewx/issues/23)) ([3b00590](https://github.com/bakerkj/ha-weewx/commit/3b00590334889000d19c5e18a779bfe4079fda71))

## [0.1.2](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.1...ha-weewx-v0.1.2) (2026-05-26)


### Bug Fixes

* clean up the release pipeline (build syslog spam + tag publish) ([#20](https://github.com/bakerkj/ha-weewx/issues/20)) ([d88286c](https://github.com/bakerkj/ha-weewx/commit/d88286cb8c562cc88f856977d13d9b315e087d44))

## [0.1.1](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.0...ha-weewx-v0.1.1) (2026-05-26)


### Features

* add WeeWX Home Assistant add-on ([004a2ab](https://github.com/bakerkj/ha-weewx/commit/004a2ab6c245a4e2fd4377b4071923a0ab5d02f3))
* bundle the MQTTSubscribe extension (bellrichm v3.1.0) ([be32c82](https://github.com/bakerkj/ha-weewx/commit/be32c82aa6cd8c6635871e793670e5c194c5ba00))


### Bug Fixes

* drop StdPrint from default report_services to stop loop-packet log spam ([4dbec53](https://github.com/bakerkj/ha-weewx/commit/4dbec53358dfb7f7530bc4249e43b13babeda7df))
* ship stock user.extensions stub so weewxd startup stops erroring ([5e4a55d](https://github.com/bakerkj/ha-weewx/commit/5e4a55db96d6914d6447f9232f0f5274c52fe622))
* track Debian apt packages via the deb datasource ([#4](https://github.com/bakerkj/ha-weewx/issues/4)) ([779b2e2](https://github.com/bakerkj/ha-weewx/commit/779b2e2267e8f9892749a58f6245011daf68b493))


### Miscellaneous Chores

* align repository.json maintainer with the LICENSE identity ([68ebf7b](https://github.com/bakerkj/ha-weewx/commit/68ebf7b655b5b13265d723d9f82155d9442ab10f))
* **deps:** update actions/upload-artifact action to v7 ([#11](https://github.com/bakerkj/ha-weewx/issues/11)) ([ed4a55b](https://github.com/bakerkj/ha-weewx/commit/ed4a55b67cd8ae1130e934a73417cfb7832c7a6f))
* **deps:** update dependency pymysql to v1.2.0 ([#6](https://github.com/bakerkj/ha-weewx/issues/6)) ([ba416ec](https://github.com/bakerkj/ha-weewx/commit/ba416eca52b68b04faecd25b427cacf650795f23))
* **deps:** update dependency pytest to v9 ([#12](https://github.com/bakerkj/ha-weewx/issues/12)) ([42f7bf1](https://github.com/bakerkj/ha-weewx/commit/42f7bf18bf3e6b9c89ea65a1722f5a6a39082f2b))
* **deps:** update dependency renovate to v43.150.0 ([#8](https://github.com/bakerkj/ha-weewx/issues/8)) ([94ee9b0](https://github.com/bakerkj/ha-weewx/commit/94ee9b0854082fa5d4b0010384cf34d2f2ba5e8f))
* **deps:** update dependency requests to v2.34.2 ([#9](https://github.com/bakerkj/ha-weewx/issues/9)) ([ec972a6](https://github.com/bakerkj/ha-weewx/commit/ec972a6f98174dfe689df33487fcfcc213130d02))
* **deps:** update docker/setup-buildx-action action to v4 ([#18](https://github.com/bakerkj/ha-weewx/issues/18)) ([690faed](https://github.com/bakerkj/ha-weewx/commit/690faedf7352f1740b207129d78c380dd15fcfcc))
* **deps:** update mariadb docker tag to v12 ([#13](https://github.com/bakerkj/ha-weewx/issues/13)) ([9c5c061](https://github.com/bakerkj/ha-weewx/commit/9c5c06186d224918fe7fe96dd2b5f9b9e3439e06))
* **deps:** update pre-commit hooks ([#5](https://github.com/bakerkj/ha-weewx/issues/5)) ([8202204](https://github.com/bakerkj/ha-weewx/commit/82022044f84325045101f1b74965ca0b6af5f9cf))
* drop build.yaml for a multiarch base-debian default ([#14](https://github.com/bakerkj/ha-weewx/issues/14)) ([452874b](https://github.com/bakerkj/ha-weewx/commit/452874bd41f92955aeb0a21fe304fb96846cf819))
* let Renovate track tag-pinned WeeWX extension versions ([30e47b9](https://github.com/bakerkj/ha-weewx/commit/30e47b9fb7fa360be33a316d59e613ff56e9ddd1))
* run Renovate Friday before 6pm ET ([#2](https://github.com/bakerkj/ha-weewx/issues/2)) ([e829070](https://github.com/bakerkj/ha-weewx/commit/e829070978aa0a4c57413427d04d85cd78d7b12d))


### Documentation

* correct the Dockerfile header to match the uv-wheels build ([#19](https://github.com/bakerkj/ha-weewx/issues/19)) ([bcfe5de](https://github.com/bakerkj/ha-weewx/commit/bcfe5dea2c2061b6555724e90848ac83ab79e2fc))


### Code Refactoring

* slim the image to ~327 MB via uv-installed wheels ([#16](https://github.com/bakerkj/ha-weewx/issues/16)) ([49a82fd](https://github.com/bakerkj/ha-weewx/commit/49a82fd535b178a55c762e5e6945f3e1f0c4397f))


### Continuous Integration

* cache the test builds via the gha layer cache ([#17](https://github.com/bakerkj/ha-weewx/issues/17)) ([4ee1756](https://github.com/bakerkj/ha-weewx/commit/4ee1756463d820d0520278e526dc681f422f159f))
* fix addon-build BUILD_FROM and drop redundant ingress_port ([dbeaaa4](https://github.com/bakerkj/ha-weewx/commit/dbeaaa4c2d2c7ae20c9f544dae366c8ac212dbbc))
* pin Python to the 3.13 series in Renovate (matches Debian trixie base) ([#15](https://github.com/bakerkj/ha-weewx/issues/15)) ([9036fb0](https://github.com/bakerkj/ha-weewx/commit/9036fb05f95a06a1439c91dd143e6ed00c5e147c))
