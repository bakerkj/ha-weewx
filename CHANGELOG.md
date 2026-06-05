# Changelog

## [0.1.12](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.11...ha-weewx-v0.1.12) (2026-06-05)


### Bug Fixes

* **build:** auto-derive rtgd unzip prefix; assert install wrote files ([#93](https://github.com/bakerkj/ha-weewx/issues/93)) ([c3ee97b](https://github.com/bakerkj/ha-weewx/commit/c3ee97b265bffc0cdd4ff45f9c49dc9683921afa))
* **build:** fail hard on extension install error; tighten weedb patch assert ([#90](https://github.com/bakerkj/ha-weewx/issues/90)) ([5da87fc](https://github.com/bakerkj/ha-weewx/commit/5da87fcb2abad990ee7e865649bc17be5a1a2d76))
* **build:** stop creating /config at build time ([#100](https://github.com/bakerkj/ha-weewx/issues/100)) ([ae4617c](https://github.com/bakerkj/ha-weewx/commit/ae4617c1575c03f3c7e6280d10efa516f7d2973a))
* **ci:** stop the push+pull_request double-fire on PR branches ([#85](https://github.com/bakerkj/ha-weewx/issues/85)) ([5edcddc](https://github.com/bakerkj/ha-weewx/commit/5edcddcbfd8fbfc42a10e324485d70e86d9a9de5))
* **ci:** use docker/build-push-action so type=gha cache actually works ([#84](https://github.com/bakerkj/ha-weewx/issues/84)) ([974632a](https://github.com/bakerkj/ha-weewx/commit/974632ae6df89ae27de3c79f39c738ad9b4f66b5))
* **image:** drop mariadb-client-core from runtime; use PyMySQL for healthcheck ([#101](https://github.com/bakerkj/ha-weewx/issues/101)) ([4982f39](https://github.com/bakerkj/ha-weewx/commit/4982f39731a60ab3d52443fe06ad82eaaf3244f3))
* **nginx:** set archive_interval Cache-Control on /NOAA/ autoindex listing ([#97](https://github.com/bakerkj/ha-weewx/issues/97)) ([fc05113](https://github.com/bakerkj/ha-weewx/commit/fc0511332850b4bfe65508cf6cb39468ade9d9ea))
* **renovate:** track WeeWX extension URLs after move to build/extensions.txt ([#79](https://github.com/bakerkj/ha-weewx/issues/79)) ([a0ad3bb](https://github.com/bakerkj/ha-weewx/commit/a0ad3bb4201a04eb97cf6e051950c57a1f3ed3ba))
* **watchdog:** warn when startup_grace is shorter than max_age ([#107](https://github.com/bakerkj/ha-weewx/issues/107)) ([a07d5db](https://github.com/bakerkj/ha-weewx/commit/a07d5dbcf11a33dcfbb5f3c4f06b1a5429ebfd6b))


### Performance Improvements

* **e2e:** shorten archive_interval to 5s in maria-mqtt + sqlite-template ([#82](https://github.com/bakerkj/ha-weewx/issues/82)) ([e846790](https://github.com/bakerkj/ha-weewx/commit/e846790e8ff7f55adb772edd8180fec46d5492bd))
* **log_to_file:** hold the output file handle open across records ([#102](https://github.com/bakerkj/ha-weewx/issues/102)) ([fa3ceb2](https://github.com/bakerkj/ha-weewx/commit/fa3ceb29c32e7ce6cfd161b15955bfde8d201a8a))


### Miscellaneous Chores

* **deps:** update dependency renovate to v43.209.2 ([#68](https://github.com/bakerkj/ha-weewx/issues/68)) ([ba04cfc](https://github.com/bakerkj/ha-weewx/commit/ba04cfc91dd6bb6bcf5e23ea8aa2fe5824b51428))
* **deps:** update dependency renovate to v43.213.0 ([#71](https://github.com/bakerkj/ha-weewx/issues/71)) ([14232bd](https://github.com/bakerkj/ha-weewx/commit/14232bdba93406f796fe58dd9a0bfe90f15fe9c0))
* **deps:** update dependency renovate to v43.213.2 ([#81](https://github.com/bakerkj/ha-weewx/issues/81)) ([12ecdf1](https://github.com/bakerkj/ha-weewx/commit/12ecdf13965ebc60aceed4521afbdb48ac7254b7))
* **deps:** update dependency renovate to v43.213.3 ([#89](https://github.com/bakerkj/ha-weewx/issues/89)) ([78d88ca](https://github.com/bakerkj/ha-weewx/commit/78d88ca6970886bff86663b996b6370b718aaa44))
* **deps:** update ghcr.io/astral-sh/uv docker tag to v0.11.19 ([#69](https://github.com/bakerkj/ha-weewx/issues/69)) ([09f2cad](https://github.com/bakerkj/ha-weewx/commit/09f2cadeb4b95378366e172020bf29c7686e98d4))
* **deps:** update github-actions ([#76](https://github.com/bakerkj/ha-weewx/issues/76)) ([807cc00](https://github.com/bakerkj/ha-weewx/commit/807cc00391cb00eeb3160085efbd6806cb572b48))
* **deps:** update github-actions to v6.0.3 ([#67](https://github.com/bakerkj/ha-weewx/issues/67)) ([6b79ceb](https://github.com/bakerkj/ha-weewx/commit/6b79ceb93069dc09535ec1bcb59759df9000f893))
* **deps:** update github-actions to v8 ([#77](https://github.com/bakerkj/ha-weewx/issues/77)) ([9146b42](https://github.com/bakerkj/ha-weewx/commit/9146b4271dee34a4cb49ac5d2f996ca3ab18570c))
* **deps:** update pre-commit hooks to v0.15.16 ([#70](https://github.com/bakerkj/ha-weewx/issues/70)) ([7ea1797](https://github.com/bakerkj/ha-weewx/commit/7ea179751bec4e075bc0f3a5238c9f9816f2830a))
* **dockerfile:** remove stale Dockerfile.test trailer comment ([#80](https://github.com/bakerkj/ha-weewx/issues/80)) ([f135ed9](https://github.com/bakerkj/ha-weewx/commit/f135ed95ad0d020e2781ca640d8803e967f39c36))
* **patches:** renumber duplicate 0005 in patches/extensions/ ([#109](https://github.com/bakerkj/ha-weewx/issues/109)) ([816f5a8](https://github.com/bakerkj/ha-weewx/commit/816f5a8b51d83f97ef84ec83d5313663815af907))
* **renovate:** enable rtgd auto-tracking; delete scripts/check-updates.sh ([#94](https://github.com/bakerkj/ha-weewx/issues/94)) ([56a9288](https://github.com/bakerkj/ha-weewx/commit/56a92881a4f26e73237a1ad2d1691514e4cd560c))


### Documentation

* clarify gauge-data.txt cache row requires rtgd ([#111](https://github.com/bakerkj/ha-weewx/issues/111)) ([d8847c7](https://github.com/bakerkj/ha-weewx/commit/d8847c7d03169a02fbd78070a13a1c2fd65d3f30))
* note that archive_interval changes need an addon restart ([#106](https://github.com/bakerkj/ha-weewx/issues/106)) ([f05854b](https://github.com/bakerkj/ha-weewx/commit/f05854b127554e3a98cff600815399144f067daa))
* **readme:** fix SQLite default path (/config/db/weewx.sdb) ([#91](https://github.com/bakerkj/ha-weewx/issues/91)) ([955eb89](https://github.com/bakerkj/ha-weewx/commit/955eb899cc176fd0cb5c2cbfb9de24e6ac1cee96))
* scrub "felddy" -&gt; "MQTT publisher (by felddy)" + history references ([#99](https://github.com/bakerkj/ha-weewx/issues/99)) ([87169cd](https://github.com/bakerkj/ha-weewx/commit/87169cdbd577f92e05e240e34107763bbe7a1aab))


### Code Refactoring

* **check_image:** named asserts with pass/fail summary ([#83](https://github.com/bakerkj/ha-weewx/issues/83)) ([c690536](https://github.com/bakerkj/ha-weewx/commit/c69053642f99762f858ae9714b3b11e74b716588))
* **ci:** extract test stage to docker-run shell script ([#74](https://github.com/bakerkj/ha-weewx/issues/74)) ([6e625b6](https://github.com/bakerkj/ha-weewx/commit/6e625b6425acb53de6d2c5edb94500410238acd2))
* **ci:** run felddy unit sweep on the host, not inside the addon image ([#98](https://github.com/bakerkj/ha-weewx/issues/98)) ([41db9ba](https://github.com/bakerkj/ha-weewx/commit/41db9ba6b97b59cceb9e9cbf7479d3c50da79c85))
* derive in-image extension assertions from extensions.txt ([#108](https://github.com/bakerkj/ha-weewx/issues/108)) ([c7d3fa0](https://github.com/bakerkj/ha-weewx/commit/c7d3fa08fb68eef92df7f0c0c407c173e186faee))
* **dockerfile:** bind-mount patches/ instead of COPY+rm ([#78](https://github.com/bakerkj/ha-weewx/issues/78)) ([a09fb6a](https://github.com/bakerkj/ha-weewx/commit/a09fb6a6cbfe201581ebed90cc9e6e45115aa811))
* **dockerfile:** extract 4 inline python heredocs to build/ scripts ([#73](https://github.com/bakerkj/ha-weewx/issues/73)) ([d257892](https://github.com/bakerkj/ha-weewx/commit/d257892e3f32fed0363f5a2582a55dca0e301aee))
* **dockerfile:** move extension URL list to build/extensions.txt ([#75](https://github.com/bakerkj/ha-weewx/issues/75)) ([3d329a7](https://github.com/bakerkj/ha-weewx/commit/3d329a7daa813c337507071532a71aedbe01d694))
* **e2e:** split maria-mqtt into mariadb + mqtt jobs, share MQTT subscriber ([#86](https://github.com/bakerkj/ha-weewx/issues/86)) ([2d9d5cb](https://github.com/bakerkj/ha-weewx/commit/2d9d5cbd5926f0784a8550580659825aa87c3585))
* **log_to_file:** rename loop_queue -&gt; record_queue; tighten test + type ([#110](https://github.com/bakerkj/ha-weewx/issues/110)) ([7f802e5](https://github.com/bakerkj/ha-weewx/commit/7f802e5d65a79187077328dbace005f1a838e264))
* **log_to_file:** test harness + extract internals + wire into CI ([#72](https://github.com/bakerkj/ha-weewx/issues/72)) ([7eee809](https://github.com/bakerkj/ha-weewx/commit/7eee809d4039ce087994a745fe27af7ca8283311))
* **patches:** move loose patches/ under patches/extensions/ ([#88](https://github.com/bakerkj/ha-weewx/issues/88)) ([46ddc23](https://github.com/bakerkj/ha-weewx/commit/46ddc2345d115425439badde2ead0461fff362bc))


### Tests

* add syslog-spam guard to mqtt + sqlite-template e2e scripts ([#105](https://github.com/bakerkj/ha-weewx/issues/105)) ([60cb24a](https://github.com/bakerkj/ha-weewx/commit/60cb24af774d4f537059f3c4a4fdff0c0e97989c))
* **check_image:** assert every entry in extensions.txt is installed ([#92](https://github.com/bakerkj/ha-weewx/issues/92)) ([54d9b28](https://github.com/bakerkj/ha-weewx/commit/54d9b2846b38a081ac7cc1e156b79e557e1d69b1))
* **mqtt:** fail the fixture loudly when the settle signal times out ([#96](https://github.com/bakerkj/ha-weewx/issues/96)) ([30f5120](https://github.com/bakerkj/ha-weewx/commit/30f51203cb3be7485fdedb9512850cb7c9a65df6))
* **watchdog:** wait for weewxd before pkill in Phase 1 ([#104](https://github.com/bakerkj/ha-weewx/issues/104)) ([0a28360](https://github.com/bakerkj/ha-weewx/commit/0a28360ec5143ac56774c31fac4fcd3dce778a6e))


### Continuous Integration

* **addon-build:** smoke-check the image per-arch before publish ([#103](https://github.com/bakerkj/ha-weewx/issues/103)) ([84f20b9](https://github.com/bakerkj/ha-weewx/commit/84f20b97b56989233cf0a8a9bdd39ea4a42e28d9))
* **prek:** cache prek hook envs across runs ([#64](https://github.com/bakerkj/ha-weewx/issues/64)) ([63ad0f4](https://github.com/bakerkj/ha-weewx/commit/63ad0f418f822efcd553f0406c3d4d79f009679a))
* **tests:** cache sidecar+e2e images; drop misleading "(cached)" step name ([#87](https://github.com/bakerkj/ha-weewx/issues/87)) ([c9e8b9a](https://github.com/bakerkj/ha-weewx/commit/c9e8b9a67b67e649d3a634bbd7b6e7c1e341e281))

## [0.1.11](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.10...ha-weewx-v0.1.11) (2026-06-01)


### Features

* bundle weewx-rain24h + weewx-xaggs with felddy metadata + tests ([#57](https://github.com/bakerkj/ha-weewx/issues/57)) ([942f9b0](https://github.com/bakerkj/ha-weewx/commit/942f9b094cc2ef8b8f3155323b93738e4ebf3fc4))


### Bug Fixes

* **felddy:** bind NEW_ARCHIVE_RECORD so archive-only fields reach MQTT ([#55](https://github.com/bakerkj/ha-weewx/issues/55)) ([d6bf635](https://github.com/bakerkj/ha-weewx/commit/d6bf6355ff942df70491421b66bd23f2af15b7f0))
* **felddy:** preserve UV index hardware precision (round 0 -&gt; 1) ([#59](https://github.com/bakerkj/ha-weewx/issues/59)) ([52b2a85](https://github.com/bakerkj/ha-weewx/commit/52b2a85867626113f174753d59029d41023b3cd8))
* **felddy:** unit_of_measurement fixes via HA-DEVICE_CLASS_UNITS sweep ([#58](https://github.com/bakerkj/ha-weewx/issues/58)) ([3b88c89](https://github.com/bakerkj/ha-weewx/commit/3b88c89e80e3496bff49ec2c54637daed3cb3b2e))


### Miscellaneous Chores

* **deps:** update dependency renovate to v43.207.4 ([#62](https://github.com/bakerkj/ha-weewx/issues/62)) ([9747b5b](https://github.com/bakerkj/ha-weewx/commit/9747b5babd0876a810ad7053100a80bc563ddb21))
* **deps:** update ghcr.io/astral-sh/uv docker tag to v0.11.18 ([#63](https://github.com/bakerkj/ha-weewx/issues/63)) ([b18b044](https://github.com/bakerkj/ha-weewx/commit/b18b0446e23d8cd32d0994168977e3c5d5b96aad))


### Continuous Integration

* **renovate:** track SHA-pinned weewx extensions via git-refs datasource ([#61](https://github.com/bakerkj/ha-weewx/issues/61)) ([c22c420](https://github.com/bakerkj/ha-weewx/commit/c22c420c388b8204b1ad04418deba05b30804feb))

## [0.1.10](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.9...ha-weewx-v0.1.10) (2026-06-01)


### Bug Fixes

* **felddy:** silence cosmetic startup warnings via KEY_CONFIG + unit helper ([#53](https://github.com/bakerkj/ha-weewx/issues/53)) ([a89ee97](https://github.com/bakerkj/ha-weewx/commit/a89ee97d85138a0a46d04aafb0a5b442daaf7e97))

## [0.1.9](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.8...ha-weewx-v0.1.9) (2026-06-01)


### Features

* split /config into /config/db (SQLite) + /config/log (log files) ([#52](https://github.com/bakerkj/ha-weewx/issues/52)) ([91099f1](https://github.com/bakerkj/ha-weewx/commit/91099f1a1bcdf2602e9c24eb8ecb0a5d6d5276a3))


### Bug Fixes

* **watchdog:** halt the container via kill -TERM 1, not s6-svscanctl ([#50](https://github.com/bakerkj/ha-weewx/issues/50)) ([b37bcf3](https://github.com/bakerkj/ha-weewx/commit/b37bcf36f52bf8e19110f95abb1855aa9f5305f6))

## [0.1.8](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.7...ha-weewx-v0.1.8) (2026-05-31)


### Features

* watchdog_startup_grace_seconds avoids the bootstrap-deadlock kill ([#49](https://github.com/bakerkj/ha-weewx/issues/49)) ([d483fe1](https://github.com/bakerkj/ha-weewx/commit/d483fe12b9eb0f8669f4611f4bd67cc08f9297e9))


### Bug Fixes

* coerce txBatteryStatus to int in felddy preprocessor ([#48](https://github.com/bakerkj/ha-weewx/issues/48)) ([9d5fd2b](https://github.com/bakerkj/ha-weewx/commit/9d5fd2bb39ca636e229276ffc711ce246875c691))


### Miscellaneous Chores

* **deps:** update dependency renovate to v43.205.2 ([#46](https://github.com/bakerkj/ha-weewx/issues/46)) ([f825c65](https://github.com/bakerkj/ha-weewx/commit/f825c65f348edb0362d98891d622243c83633501))

## [0.1.7](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.6...ha-weewx-v0.1.7) (2026-05-31)


### Features

* enable udev so /dev/serial/by-id/usb-* symlinks are exposed ([#44](https://github.com/bakerkj/ha-weewx/issues/44)) ([8c5313e](https://github.com/bakerkj/ha-weewx/commit/8c5313ecaf6fffcc44f4e6dda70032048ec5fd9e))

## [0.1.6](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.5...ha-weewx-v0.1.6) (2026-05-29)


### Features

* exit the addon when weewxd or nginx fails ([#41](https://github.com/bakerkj/ha-weewx/issues/41)) ([fc3c9ce](https://github.com/bakerkj/ha-weewx/commit/fc3c9ce4f7b8b56de7dd2e784c6c61cd15acd357))


### Miscellaneous Chores

* **deps:** update dependency renovate to v43.204.0 ([#42](https://github.com/bakerkj/ha-weewx/issues/42)) ([658c0a9](https://github.com/bakerkj/ha-weewx/commit/658c0a900614cf67fc55b2c4fe9bb43f60f33d58))

## [0.1.5](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.4...ha-weewx-v0.1.5) (2026-05-29)


### Bug Fixes

* quote MariaDB reserved words in weedb instead of renaming forecast columns ([#40](https://github.com/bakerkj/ha-weewx/issues/40)) ([0e344bb](https://github.com/bakerkj/ha-weewx/commit/0e344bb3c644d087ac1f9bf5cf39c23a4e8284a0))


### Miscellaneous Chores

* **deps:** update dependency renovate to v43.202.0 ([#38](https://github.com/bakerkj/ha-weewx/issues/38)) ([afb13c2](https://github.com/bakerkj/ha-weewx/commit/afb13c20d568c029c8b3b43a1b3f4c1c81842700))
* **deps:** update dependency renovate to v43.202.1 ([#39](https://github.com/bakerkj/ha-weewx/issues/39)) ([626beee](https://github.com/bakerkj/ha-weewx/commit/626beee4b5aa3a9649c3af4736bf9f9e29e67959))
* **deps:** update ghcr.io/astral-sh/uv docker tag to v0.11.17 ([#36](https://github.com/bakerkj/ha-weewx/issues/36)) ([38ae580](https://github.com/bakerkj/ha-weewx/commit/38ae580a32de12189892bd7a791bc20875b88ec6))
* **deps:** update pre-commit hook astral-sh/ruff-pre-commit to v0.15.15 ([#37](https://github.com/bakerkj/ha-weewx/issues/37)) ([591ada8](https://github.com/bakerkj/ha-weewx/commit/591ada8b6b22bc202db378d0e84544ee4ea88e6e))


### Tests

* first-boot smoke test + rtgd guard build-check ([#32](https://github.com/bakerkj/ha-weewx/issues/32)) ([38c1ccd](https://github.com/bakerkj/ha-weewx/commit/38c1ccdc0aa92039b42f7be412a74d17242c0f2e))
* rename e2e suite consistently + restore reworks + speed up ([#34](https://github.com/bakerkj/ha-weewx/issues/34)) ([717fa6f](https://github.com/bakerkj/ha-weewx/commit/717fa6fbcfa30ca8617bd25a804cd38a2e8e2909))

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
