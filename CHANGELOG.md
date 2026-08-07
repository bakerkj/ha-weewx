# Changelog

## [0.1.31](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.30...ha-weewx-v0.1.31) (2026-08-07)


### Features

* **ci:** add weewx-diff reviewer for Renovate PRs ([#276](https://github.com/bakerkj/ha-weewx/issues/276)) ([b35c786](https://github.com/bakerkj/ha-weewx/commit/b35c7862810b0a6a04e09c22369032ad11bd8eda))


### Bug Fixes

* **build:** retry install_rtgd.py + xstats.py fetches on transient failures ([#281](https://github.com/bakerkj/ha-weewx/issues/281)) ([63a82e1](https://github.com/bakerkj/ha-weewx/commit/63a82e1742fb5dfe81ffeba50e2f963b352dd5fc))
* **build:** retry weectl extension install on transient failures ([#278](https://github.com/bakerkj/ha-weewx/issues/278)) ([79a2852](https://github.com/bakerkj/ha-weewx/commit/79a2852c91303c3dd79227e1454bc0f4951cd0e5))
* **deps:** update weewx to v5.5.0 ([#273](https://github.com/bakerkj/ha-weewx/issues/273)) ([284eb57](https://github.com/bakerkj/ha-weewx/commit/284eb57d393a79b8a525214b62e001afbf71d190))
* **pre-commit:** set default_stages so hooks skip commit-msg by default ([#271](https://github.com/bakerkj/ha-weewx/issues/271)) ([5f7abdc](https://github.com/bakerkj/ha-weewx/commit/5f7abdc6bf67156f3624ef3d07ecfc134331aa6b))
* **renovate:** add minimumGroupSize:2 to uv tool group ([#268](https://github.com/bakerkj/ha-weewx/issues/268)) ([c083e04](https://github.com/bakerkj/ha-weewx/commit/c083e042e1c9444b6d1fa5639ed8e65d114c7c0e))
* **renovate:** group both weewx pins so they bump atomically ([#272](https://github.com/bakerkj/ha-weewx/issues/272)) ([61cb11e](https://github.com/bakerkj/ha-weewx/commit/61cb11e00b2a74b49ea3c9dda4cb548f71d33e67))
* **renovate:** group frenck/action-addon-linter pins atomically ([#274](https://github.com/bakerkj/ha-weewx/issues/274)) ([1b49456](https://github.com/bakerkj/ha-weewx/commit/1b494564c604a128835a4b4c61303a25ee1a42ac))
* **renovate:** make uv tool group symmetric + atomic ([#270](https://github.com/bakerkj/ha-weewx/issues/270)) ([4ae3c81](https://github.com/bakerkj/ha-weewx/commit/4ae3c81ebf8312a95e30188ac8accd2f8aa3e930))
* scope dev-tooling auto-merge by depType ([#264](https://github.com/bakerkj/ha-weewx/issues/264)) ([5300a23](https://github.com/bakerkj/ha-weewx/commit/5300a23dbae027a3e4133d1a4c2edc5586160972))


### Miscellaneous Chores

* **deps:** update anthropics/claude-code-action action to v1.0.182 ([#252](https://github.com/bakerkj/ha-weewx/issues/252)) ([92749e5](https://github.com/bakerkj/ha-weewx/commit/92749e50d3aab69c5638988bc83f5353724a6243))
* **deps:** update anthropics/claude-code-action action to v1.0.183 ([#260](https://github.com/bakerkj/ha-weewx/issues/260)) ([32bc6d5](https://github.com/bakerkj/ha-weewx/commit/32bc6d53e301d3eb65e46d1e7527ef0b4f9e53da))
* **deps:** update anthropics/claude-code-action action to v1.0.184 ([#275](https://github.com/bakerkj/ha-weewx/issues/275)) ([59ee5e8](https://github.com/bakerkj/ha-weewx/commit/59ee5e8161fe878199fa2bcf42493716ee134365))
* **deps:** update anthropics/claude-code-action action to v1.0.186 ([#279](https://github.com/bakerkj/ha-weewx/issues/279)) ([ebcb98f](https://github.com/bakerkj/ha-weewx/commit/ebcb98feb51709c6c180ebce89e50988726c909b))
* **deps:** update dependency chaunceygardiner/weewx-forecast to v5.1 ([#277](https://github.com/bakerkj/ha-weewx/issues/277)) ([13316b6](https://github.com/bakerkj/ha-weewx/commit/13316b6b7c0ed739087e8bb6dcf27727f03010d4))
* **deps:** update dependency renovate to v43.280.3 ([#253](https://github.com/bakerkj/ha-weewx/issues/253)) ([6316f62](https://github.com/bakerkj/ha-weewx/commit/6316f62c36ffbf7ab447a01a5122a3e365ba94cb))
* **deps:** update dependency renovate to v44 ([#257](https://github.com/bakerkj/ha-weewx/issues/257)) ([a9941ae](https://github.com/bakerkj/ha-weewx/commit/a9941aea212ddd4b64c9a3d78ba62a543c31b84b))
* **deps:** update dependency renovate to v44.10.0 ([#280](https://github.com/bakerkj/ha-weewx/issues/280)) ([80d663c](https://github.com/bakerkj/ha-weewx/commit/80d663cc712235ca7fb7918043effc26f2d23060))
* **deps:** update dependency renovate to v44.5.2 ([#261](https://github.com/bakerkj/ha-weewx/issues/261)) ([9d44263](https://github.com/bakerkj/ha-weewx/commit/9d442639c79d8e130e557bc7e760053dc19ba87f))
* **deps:** update dependency renovate to v44.7.2 ([#266](https://github.com/bakerkj/ha-weewx/issues/266)) ([33d7b75](https://github.com/bakerkj/ha-weewx/commit/33d7b75f2d4b4ba21de7d363729ca7cc3fa385e2))
* **deps:** update j178/prek-action action to v3 ([#259](https://github.com/bakerkj/ha-weewx/issues/259)) ([6f134cf](https://github.com/bakerkj/ha-weewx/commit/6f134cf21c3e357dd5813a3ba44ad94eb6660ff4))
* **deps:** update pre-commit hook aleksac/hadolint-py to v2.15.1 ([#265](https://github.com/bakerkj/ha-weewx/issues/265)) ([5054e84](https://github.com/bakerkj/ha-weewx/commit/5054e84bcfafeea1a9156790249739bd8395bf08))
* **deps:** update pre-commit hook astral-sh/ruff-pre-commit to v0.16.1 ([#258](https://github.com/bakerkj/ha-weewx/issues/258)) ([5a371d3](https://github.com/bakerkj/ha-weewx/commit/5a371d3f4b322772fdd8aa3560cee61897a93e72))
* **deps:** update uv tool to v0.12.0 ([#256](https://github.com/bakerkj/ha-weewx/issues/256)) ([0e2c2e8](https://github.com/bakerkj/ha-weewx/commit/0e2c2e868ea61314737271c1018f76b051f51f6d))
* **deps:** update uv tool to v0.12.1 ([#262](https://github.com/bakerkj/ha-weewx/issues/262)) ([2cb697b](https://github.com/bakerkj/ha-weewx/commit/2cb697b9af685f5979e7b46eee69160396e1f1ed))
* **deps:** update uv tool to v0.12.2 ([#269](https://github.com/bakerkj/ha-weewx/issues/269)) ([5e405b9](https://github.com/bakerkj/ha-weewx/commit/5e405b92a9a6f0283e1bdff6a1e32b599762691d))
* manage pyproject and uv.lock version via release-please ([#255](https://github.com/bakerkj/ha-weewx/issues/255)) ([426a4fc](https://github.com/bakerkj/ha-weewx/commit/426a4fc56ca59502ca08766299664a4e54d70c22))


### Continuous Integration

* enable renovate auto-merge for CI-only updates ([#263](https://github.com/bakerkj/ha-weewx/issues/263)) ([e74bfe8](https://github.com/bakerkj/ha-weewx/commit/e74bfe844fcbf037407b6d5e9c650043d44d4bad))

## [0.1.30](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.29...ha-weewx-v0.1.30) (2026-07-24)


### Bug Fixes

* **e2e:** close birth-race in mqtt discovery fixture ([#245](https://github.com/bakerkj/ha-weewx/issues/245)) ([d729d40](https://github.com/bakerkj/ha-weewx/commit/d729d40ff9ca1abe6798d3f6df5de9a1ec8355a5))


### Miscellaneous Chores

* **deps:** update anthropics/claude-code-action action to v1.0.181 ([#250](https://github.com/bakerkj/ha-weewx/issues/250)) ([524d960](https://github.com/bakerkj/ha-weewx/commit/524d960270507eee7427cc09f0a8fbf9ba1727cf))
* **deps:** update astral-sh/setup-uv action to v9 ([#243](https://github.com/bakerkj/ha-weewx/issues/243)) ([ff90399](https://github.com/bakerkj/ha-weewx/commit/ff90399a841a29ff0bc81d419996cdc69fda706e))
* **deps:** update dependency @commitlint/config-conventional to v21 ([#240](https://github.com/bakerkj/ha-weewx/issues/240)) ([ebadd0b](https://github.com/bakerkj/ha-weewx/commit/ebadd0b42ede9485a9f8a776c6fc48c727980ce3))
* **deps:** update dependency chaunceygardiner/weewx-forecast to v5.0.1 ([#249](https://github.com/bakerkj/ha-weewx/issues/249)) ([94564b9](https://github.com/bakerkj/ha-weewx/commit/94564b9fb5a8760877c1857890dbade14d5fa3b2))
* **deps:** update dependency renovate to v43.280.0 ([#251](https://github.com/bakerkj/ha-weewx/issues/251)) ([356b616](https://github.com/bakerkj/ha-weewx/commit/356b616fb3cadaccd919cf2cac02070c57fd4f7b))
* **deps:** update github-actions ([#238](https://github.com/bakerkj/ha-weewx/issues/238)) ([a2afee0](https://github.com/bakerkj/ha-weewx/commit/a2afee01889c3595c1ca485f2374ace2f5e905ee))
* **deps:** update pre-commit hook astral-sh/ruff-pre-commit to v0.16.0 ([#246](https://github.com/bakerkj/ha-weewx/issues/246)) ([07fdae3](https://github.com/bakerkj/ha-weewx/commit/07fdae3033929163a87ad038ebe53b356d08a48f))
* **deps:** update pre-commit hook rbubley/mirrors-prettier to v3.9.6 ([#242](https://github.com/bakerkj/ha-weewx/issues/242)) ([be83be8](https://github.com/bakerkj/ha-weewx/commit/be83be8d2f804fde9486dc80686f2d40b1b2ac65))
* **deps:** update uv tool to v0.11.30 ([#236](https://github.com/bakerkj/ha-weewx/issues/236)) ([2c94a85](https://github.com/bakerkj/ha-weewx/commit/2c94a85d9e67cc220e4a66eb0a244f30302502ae))
* **deps:** update uv tool to v0.11.31 ([#244](https://github.com/bakerkj/ha-weewx/issues/244)) ([c08b5e7](https://github.com/bakerkj/ha-weewx/commit/c08b5e750c21cbad4997c4c8909ff8ea962dde2a))
* **deps:** update uv tool to v0.11.32 ([#248](https://github.com/bakerkj/ha-weewx/issues/248)) ([5ab2302](https://github.com/bakerkj/ha-weewx/commit/5ab2302ac15a139a9e6e7027034188602180eb7a))
* **renovate:** close config gaps found across sibling repos ([#239](https://github.com/bakerkj/ha-weewx/issues/239)) ([044ee14](https://github.com/bakerkj/ha-weewx/commit/044ee1438bedb63db09a33f81dd6cfe7f3a86ec7))
* **renovate:** drop redundant alternation in npm-in-pre-commit regex ([#241](https://github.com/bakerkj/ha-weewx/issues/241)) ([ea1fd7c](https://github.com/bakerkj/ha-weewx/commit/ea1fd7c21f95cb581b2964dfacba9549e32e4eab))

## [0.1.29](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.28...ha-weewx-v0.1.29) (2026-07-19)


### Features

* **extensions:** bundle weatherflow-udp Tempest station driver ([#235](https://github.com/bakerkj/ha-weewx/issues/235)) ([b87ffa3](https://github.com/bakerkj/ha-weewx/commit/b87ffa3f805bd40b542da3ad7c6fc88e59be41aa))


### Miscellaneous Chores

* **deps:** update github-actions ([#233](https://github.com/bakerkj/ha-weewx/issues/233)) ([8eb522b](https://github.com/bakerkj/ha-weewx/commit/8eb522be4f0cd48e163781cb3b79561e60218418))

## [0.1.28](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.27...ha-weewx-v0.1.28) (2026-07-18)


### Features

* **nginx:** /config/nginx-extra.conf user override for server-scope directives ([#229](https://github.com/bakerkj/ha-weewx/issues/229)) ([bd7f990](https://github.com/bakerkj/ha-weewx/commit/bd7f990f40273adfa0a5c221175e1aec46127e94))
* **refresh_stale_outputs:** age-out stale_age-gated outputs on weewx.STARTUP ([#230](https://github.com/bakerkj/ha-weewx/issues/230)) ([abc7061](https://github.com/bakerkj/ha-weewx/commit/abc7061b37e0206723774d666b7cf216e4212f7d))


### Bug Fixes

* **patches/weewx:** atomic weeutil.deep_copy_path (tmp + os.replace) ([#231](https://github.com/bakerkj/ha-weewx/issues/231)) ([c17f9a6](https://github.com/bakerkj/ha-weewx/commit/c17f9a60ca5472e2a54dae0291caeb0328b4b128))


### Miscellaneous Chores

* **deps:** update anthropics/claude-code-action action to v1.0.177 ([#224](https://github.com/bakerkj/ha-weewx/issues/224)) ([1101aeb](https://github.com/bakerkj/ha-weewx/commit/1101aeb3e3bd707a580a5a3bd45a7577a6828d5c))
* **deps:** update dependency renovate to v43.270.0 ([#225](https://github.com/bakerkj/ha-weewx/issues/225)) ([584b9ce](https://github.com/bakerkj/ha-weewx/commit/584b9cee593c0cde5d7b68fb587d2b745b736387))


### Code Refactoring

* **nginx:** regex-ify /robots.txt + /gauge-data.txt tiers for extras-overridability ([#232](https://github.com/bakerkj/ha-weewx/issues/232)) ([55b89ad](https://github.com/bakerkj/ha-weewx/commit/55b89adb70cded4c2fe8635605c7baa90c4e999c))

## [0.1.27](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.26...ha-weewx-v0.1.27) (2026-07-18)


### Code Refactoring

* **report_hook:** drop HA-options integration, weewx.conf-only config ([#226](https://github.com/bakerkj/ha-weewx/issues/226)) ([fe276e1](https://github.com/bakerkj/ha-weewx/commit/fe276e114f314f6b49eff611226cbfdf60847193))

## [0.1.26](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.25...ha-weewx-v0.1.26) (2026-07-18)


### Features

* **report_hook:** bundled ReportGenerator for post-report shell hooks ([#223](https://github.com/bakerkj/ha-weewx/issues/223)) ([7642563](https://github.com/bakerkj/ha-weewx/commit/764256395ec839fa48225947f982197c51a34fbc))


### Bug Fixes

* **nginx:** align default cache tiers with actual regen cadence ([#222](https://github.com/bakerkj/ha-weewx/issues/222)) ([e249bb6](https://github.com/bakerkj/ha-weewx/commit/e249bb6730bd1244c8c54d89ca3cf6e271836fab))


### Miscellaneous Chores

* **deps:** update anthropics/claude-code-action action to v1.0.176 ([#217](https://github.com/bakerkj/ha-weewx/issues/217)) ([a00d29f](https://github.com/bakerkj/ha-weewx/commit/a00d29f9dd9e8a0847dde72337c5d3c90aafa684))
* **deps:** update dependency chaunceygardiner/weewx-forecast to v5 ([#221](https://github.com/bakerkj/ha-weewx/issues/221)) ([8bc83fd](https://github.com/bakerkj/ha-weewx/commit/8bc83fd13bdf668be858a3f9044a997f9a772fba))
* **deps:** update dependency renovate to v43.268.0 ([#212](https://github.com/bakerkj/ha-weewx/issues/212)) ([08cc4f1](https://github.com/bakerkj/ha-weewx/commit/08cc4f15e64e568e4c8545ad212499317526b216))
* **deps:** update dependency renovate to v43.268.2 ([#219](https://github.com/bakerkj/ha-weewx/issues/219)) ([db8c501](https://github.com/bakerkj/ha-weewx/commit/db8c501474d07867d000b0d3c31955b4b6b167d7))
* **deps:** update dependency renovate to v43.268.4 ([#220](https://github.com/bakerkj/ha-weewx/issues/220)) ([77bb2a9](https://github.com/bakerkj/ha-weewx/commit/77bb2a9fc96494554ff35a63cbc085bc3e5a27ee))
* **deps:** update pre-commit hook astral-sh/ruff-pre-commit to v0.15.22 ([#216](https://github.com/bakerkj/ha-weewx/issues/216)) ([71fcf6a](https://github.com/bakerkj/ha-weewx/commit/71fcf6a239a33e131bbdbff64fea5fd7839c2fa5))
* **deps:** update pre-commit hook codespell-project/codespell to v2.4.3 ([#213](https://github.com/bakerkj/ha-weewx/issues/213)) ([605fc43](https://github.com/bakerkj/ha-weewx/commit/605fc43971520440d784a977b4ec13fdcc3f4f99))
* **deps:** update uv tool to v0.11.29 ([#215](https://github.com/bakerkj/ha-weewx/issues/215)) ([4a896da](https://github.com/bakerkj/ha-weewx/commit/4a896daec9d7f67f0e1b6aeca2a9517c5a714f80))
* **renovate:** route trixie-{updates,security} via github-apt-helper proxy ([#218](https://github.com/bakerkj/ha-weewx/issues/218)) ([6f8fb24](https://github.com/bakerkj/ha-weewx/commit/6f8fb24e670cb32c510b06328e255ebfdca97f83))

## [0.1.25](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.24...ha-weewx-v0.1.25) (2026-07-15)


### Miscellaneous Chores

* **deps:** update actions/setup-node action to v7 ([#207](https://github.com/bakerkj/ha-weewx/issues/207)) ([3aa7be6](https://github.com/bakerkj/ha-weewx/commit/3aa7be689140fa2bfcbed88d35d3118ff331c444))
* **deps:** update dependency chaunceygardiner/weewx-forecast to v4.2 ([#204](https://github.com/bakerkj/ha-weewx/issues/204)) ([0b0a079](https://github.com/bakerkj/ha-weewx/commit/0b0a079adc46d5a060da6e0a215aa92337a84be4))
* **deps:** update dependency renovate to v43.263.2 ([#209](https://github.com/bakerkj/ha-weewx/issues/209)) ([e1c6763](https://github.com/bakerkj/ha-weewx/commit/e1c6763566701657088478fe1afd52eb94b87641))
* **deps:** update github-actions ([#206](https://github.com/bakerkj/ha-weewx/issues/206)) ([dd60583](https://github.com/bakerkj/ha-weewx/commit/dd60583a9c2700072789198b1c061213dd171554))


### Build System

* add xtide-builder stage for tide predictions ([#211](https://github.com/bakerkj/ha-weewx/issues/211)) ([89f6349](https://github.com/bakerkj/ha-weewx/commit/89f6349d2c1d9120b06e2e10768510d81aef14cf))
* switch rtldavis-builder base to debian:13.6 with digest pin ([#210](https://github.com/bakerkj/ha-weewx/issues/210)) ([40e64ec](https://github.com/bakerkj/ha-weewx/commit/40e64ecf16ed414b0106dc1703ae69b235c738fb))

## [0.1.24](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.23...ha-weewx-v0.1.24) (2026-07-13)


### Miscellaneous Chores

* **deps:** pin base-debian to CalVer + digest ([#186](https://github.com/bakerkj/ha-weewx/issues/186)) ([b72e863](https://github.com/bakerkj/ha-weewx/commit/b72e863e503330939129182968d7bc44902d2133))
* **deps:** update actions/cache action to v6 ([#188](https://github.com/bakerkj/ha-weewx/issues/188)) ([fbe6762](https://github.com/bakerkj/ha-weewx/commit/fbe6762375a3b6f80d3eb6a0d61f8e70ba89abd3))
* **deps:** update apt packages ([#203](https://github.com/bakerkj/ha-weewx/issues/203)) ([463ea2f](https://github.com/bakerkj/ha-weewx/commit/463ea2f34d42cee1ef18c07397f5024778695c18))
* **deps:** update astral-sh/setup-uv action to v8.3.0 ([#197](https://github.com/bakerkj/ha-weewx/issues/197)) ([3aa1d28](https://github.com/bakerkj/ha-weewx/commit/3aa1d2847529728ab7dbdd3297852a286587336a))
* **deps:** update debian docker tag to trixie-20260623 ([#191](https://github.com/bakerkj/ha-weewx/issues/191)) ([ebd73e6](https://github.com/bakerkj/ha-weewx/commit/ebd73e69788b047a6f65fdb6ad14c3703111d38f))
* **deps:** update dependency nginx-light to v1.26.3-3+deb13u7 ([#195](https://github.com/bakerkj/ha-weewx/issues/195)) ([66d75dd](https://github.com/bakerkj/ha-weewx/commit/66d75dd7b8b841b0a0dbca12db8ba3bb58d5c033))
* **deps:** update dependency renovate to v43.251.3 ([#192](https://github.com/bakerkj/ha-weewx/issues/192)) ([bb38d5f](https://github.com/bakerkj/ha-weewx/commit/bb38d5f73a7ba94b93501e1fba7ca1ed98498a9c))
* **deps:** update dependency renovate to v43.257.5 ([#201](https://github.com/bakerkj/ha-weewx/issues/201)) ([ed266ba](https://github.com/bakerkj/ha-weewx/commit/ed266ba8f74af790ee7de2bc672ccb64a9af4ba7))
* **deps:** update github-actions ([#194](https://github.com/bakerkj/ha-weewx/issues/194)) ([145e37b](https://github.com/bakerkj/ha-weewx/commit/145e37bc98354e5d6e4fe7682fa468e3182ab092))
* **deps:** update github-actions ([#199](https://github.com/bakerkj/ha-weewx/issues/199)) ([6053f93](https://github.com/bakerkj/ha-weewx/commit/6053f93312e2887c47eb429aa2ed15adfb2a0caa))
* **deps:** update pre-commit hooks ([#190](https://github.com/bakerkj/ha-weewx/issues/190)) ([54c31f2](https://github.com/bakerkj/ha-weewx/commit/54c31f2ff0a151f2bcc7e58dc853af8c4fd498e0))
* **deps:** update pre-commit hooks ([#193](https://github.com/bakerkj/ha-weewx/issues/193)) ([21e897a](https://github.com/bakerkj/ha-weewx/commit/21e897a1cee211151138a774cade8f62215ae63e))
* **deps:** update pre-commit hooks ([#200](https://github.com/bakerkj/ha-weewx/issues/200)) ([d7d704f](https://github.com/bakerkj/ha-weewx/commit/d7d704f7904ad4499acf7040c9d771122b3918dd))
* **deps:** update uv tool to v0.11.24 ([#189](https://github.com/bakerkj/ha-weewx/issues/189)) ([48882e6](https://github.com/bakerkj/ha-weewx/commit/48882e6486196bbbccccc201ba66f7384ce3a498))
* **deps:** update uv tool to v0.11.26 ([#196](https://github.com/bakerkj/ha-weewx/issues/196)) ([0290d54](https://github.com/bakerkj/ha-weewx/commit/0290d54cdf4e8aea35e66d5f435ba4a786ccc38b))
* **deps:** update uv tool to v0.11.28 ([#198](https://github.com/bakerkj/ha-weewx/issues/198)) ([4f07e34](https://github.com/bakerkj/ha-weewx/commit/4f07e34295fe3520a0d2a3024e0c5012d2fde5d8))


### Build System

* add .dockerignore to trim CI build context ([#202](https://github.com/bakerkj/ha-weewx/issues/202)) ([8747440](https://github.com/bakerkj/ha-weewx/commit/87474404314b65aef4aa30e308b81da5b380127f))

## [0.1.23](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.22...ha-weewx-v0.1.23) (2026-06-20)


### Features

* **nginx:** stale-while-revalidate on gauge-data.txt to kill inter-page flash ([#183](https://github.com/bakerkj/ha-weewx/issues/183)) ([fa93382](https://github.com/bakerkj/ha-weewx/commit/fa93382673c019ea9cc8a0cde88668904659690a))


### Bug Fixes

* **renovate:** home-assistant/builder regex must survive digest pin ([#182](https://github.com/bakerkj/ha-weewx/issues/182)) ([235b781](https://github.com/bakerkj/ha-weewx/commit/235b781375bd2bef2987e2574cb7b41888802888))


### Miscellaneous Chores

* **deps:** pin dependencies ([#178](https://github.com/bakerkj/ha-weewx/issues/178)) ([2c9f244](https://github.com/bakerkj/ha-weewx/commit/2c9f244a62cac4f4a5bd373c608c9a5e7fd06191))
* **deps:** update dependency pytest to v9.1.1 ([#185](https://github.com/bakerkj/ha-weewx/issues/185)) ([4a6c8ba](https://github.com/bakerkj/ha-weewx/commit/4a6c8ba17011202f19b9522cab4c2a3c1050c492))
* **deps:** update dependency renovate to v43.232.0 ([#176](https://github.com/bakerkj/ha-weewx/issues/176)) ([5c34793](https://github.com/bakerkj/ha-weewx/commit/5c347939be71d3b42d1c2d8e0816bfd71dac158b))
* **deps:** update github-actions to v7 ([#177](https://github.com/bakerkj/ha-weewx/issues/177)) ([5f172ce](https://github.com/bakerkj/ha-weewx/commit/5f172ce078f7e7d1da025d544d4622ff6e3c0b24))
* **deps:** update pre-commit hooks to v0.15.18 ([#173](https://github.com/bakerkj/ha-weewx/issues/173)) ([3ce2181](https://github.com/bakerkj/ha-weewx/commit/3ce2181d600c607644685d2c6b15fc5b4210bd01))
* **deps:** update uv tool to v0.11.22 ([#174](https://github.com/bakerkj/ha-weewx/issues/174)) ([1b35dcd](https://github.com/bakerkj/ha-weewx/commit/1b35dcdc025a00a760bb5f8f070c06b4e8e10196))
* **deps:** update uv tool to v0.11.23 ([#184](https://github.com/bakerkj/ha-weewx/issues/184)) ([02a46c2](https://github.com/bakerkj/ha-weewx/commit/02a46c244b28dcde03056904b6a7bf32a753cfc4))
* normalize workflow file extensions to .yaml ([#179](https://github.com/bakerkj/ha-weewx/issues/179)) ([13dd278](https://github.com/bakerkj/ha-weewx/commit/13dd27880469c54ee2f5a33f4a3097a0df1e91b3))
* pin GitHub Actions to triple-digit tags ([#171](https://github.com/bakerkj/ha-weewx/issues/171)) ([9a41e75](https://github.com/bakerkj/ha-weewx/commit/9a41e75eb2cf57602bdb9a4633792c13f4890d96))
* **renovate:** pin GitHub Action digests to semver ([#175](https://github.com/bakerkj/ha-weewx/issues/175)) ([c6c344e](https://github.com/bakerkj/ha-weewx/commit/c6c344e8b591fb81233011dd999a0f329af5bdca))

## [0.1.22](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.21...ha-weewx-v0.1.22) (2026-06-16)


### Bug Fixes

* **deps:** update dependency weewx to v5.4.0 ([#170](https://github.com/bakerkj/ha-weewx/issues/170)) ([baa7ac0](https://github.com/bakerkj/ha-weewx/commit/baa7ac055ca7fdc64f388a2e78d80052b550e472))


### Miscellaneous Chores

* **deps:** update dependency renovate to v43.227.0 ([#168](https://github.com/bakerkj/ha-weewx/issues/168)) ([167ddab](https://github.com/bakerkj/ha-weewx/commit/167ddab664dd42b2392b46260bac3a8ae9a00096))
* **deps:** update weewx extensions to v2026.06.0 ([#167](https://github.com/bakerkj/ha-weewx/issues/167)) ([a43c74f](https://github.com/bakerkj/ha-weewx/commit/a43c74fa83f2264a038cde7210d17bcf3941c5ae))
* **deps:** update weewx extensions to v5.4.0 ([#169](https://github.com/bakerkj/ha-weewx/issues/169)) ([3f29035](https://github.com/bakerkj/ha-weewx/commit/3f2903565d27cb2a6738c3ba029877ea31b42ce0))


### Continuous Integration

* add .mypy_cache step + setup-uv cache-suffix + step name cleanup ([#165](https://github.com/bakerkj/ha-weewx/issues/165)) ([4d8519b](https://github.com/bakerkj/ha-weewx/commit/4d8519b1ea27e967b0cd599c7f265968c935cc95))

## [0.1.21](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.20...ha-weewx-v0.1.21) (2026-06-15)


### Bug Fixes

* **rtgd:** strftime route in 0016 default-fallback for time aggregates ([#162](https://github.com/bakerkj/ha-weewx/issues/162)) ([26ca600](https://github.com/bakerkj/ha-weewx/commit/26ca6004d6feffab4414832a1941ae95a13ec426))

## [0.1.20](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.19...ha-weewx-v0.1.20) (2026-06-15)


### Bug Fixes

* **rtgd:** real fix for appTemp KeyError + 0015 constructor guard + e2e ([#159](https://github.com/bakerkj/ha-weewx/issues/159)) ([389f5f0](https://github.com/bakerkj/ha-weewx/commit/389f5f09bca5e817d346cddfeba8753303860a39))

## [0.1.19](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.18...ha-weewx-v0.1.19) (2026-06-15)


### Features

* **rtgd:** skip empty-source FieldMap entries; gate _emit_tick on first LOOP ([#158](https://github.com/bakerkj/ha-weewx/issues/158)) ([17536f4](https://github.com/bakerkj/ha-weewx/commit/17536f4306da1e5eb5300c551f6067dea6e76e87))


### Miscellaneous Chores

* **checks:** integration tests for the 14 extension patches inside the image ([#156](https://github.com/bakerkj/ha-weewx/issues/156)) ([7284ab0](https://github.com/bakerkj/ha-weewx/commit/7284ab0522b826b658189694f8e05f7679f1da01))

## [0.1.18](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.17...ha-weewx-v0.1.18) (2026-06-14)


### Bug Fixes

* **rtgd:** round tick_interval ts to nearest second ([#153](https://github.com/bakerkj/ha-weewx/issues/153)) ([79c8900](https://github.com/bakerkj/ha-weewx/commit/79c8900bff0608e02ddb0d12920f8f8eabf2c05c))

## [0.1.17](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.16...ha-weewx-v0.1.17) (2026-06-14)


### Features

* **rtgd:** tick_interval option for monotonic gauge-data.txt clock ([#150](https://github.com/bakerkj/ha-weewx/issues/150)) ([4a2b65f](https://github.com/bakerkj/ha-weewx/commit/4a2b65f9ef6607c4f477a37f0f23f4c4bf3def18))


### Miscellaneous Chores

* **review:** instruct review bot to preserve patch-file diff format ([#151](https://github.com/bakerkj/ha-weewx/issues/151)) ([ee6f137](https://github.com/bakerkj/ha-weewx/commit/ee6f1376fe827d3ed87534372b966de5b2a2b22c))

## [0.1.16](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.15...ha-weewx-v0.1.16) (2026-06-14)


### Miscellaneous Chores

* **deps:** bump weewx-purpleair to v0.10 ([#146](https://github.com/bakerkj/ha-weewx/issues/146)) ([017bf38](https://github.com/bakerkj/ha-weewx/commit/017bf3883d1eb36e6022278a6e16e8c6f7d8eb8e))
* **deps:** update debian docker tag to trixie-20260610 ([#143](https://github.com/bakerkj/ha-weewx/issues/143)) ([43682da](https://github.com/bakerkj/ha-weewx/commit/43682dabcf27eb0f5cc9423123c826ffa8e02d59))
* **deps:** update dependency pytest to v9.1.0 ([#149](https://github.com/bakerkj/ha-weewx/issues/149)) ([e23c749](https://github.com/bakerkj/ha-weewx/commit/e23c749e0c7076d4b36b4414d658bccf870a4a0c))
* **deps:** update pre-commit hooks to v0.15.17 ([#144](https://github.com/bakerkj/ha-weewx/issues/144)) ([6a813ef](https://github.com/bakerkj/ha-weewx/commit/6a813efcbbcde7f962d13a4a5fcd1d7a69919995))
* **deps:** update pre-commit hooks to v0.37.3 ([#148](https://github.com/bakerkj/ha-weewx/issues/148)) ([e343c09](https://github.com/bakerkj/ha-weewx/commit/e343c090eb71a72fc8b58c0d7e1bdbe66fb2268a))
* **deps:** update uv tool to v0.11.21 ([#147](https://github.com/bakerkj/ha-weewx/issues/147)) ([b944a53](https://github.com/bakerkj/ha-weewx/commit/b944a530ebd029d4adc340443eb7f31a5bff910b))

## [0.1.15](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.14...ha-weewx-v0.1.15) (2026-06-11)


### Features

* **rtldavis:** bundle SDR receiver as opt-in Davis alternative ([#141](https://github.com/bakerkj/ha-weewx/issues/141)) ([c76001b](https://github.com/bakerkj/ha-weewx/commit/c76001b3463036cdd653dacbd833dbda7ab3c6b2))
* **version:** log ha-weewx version on startup ([#132](https://github.com/bakerkj/ha-weewx/issues/132)) ([cdfc006](https://github.com/bakerkj/ha-weewx/commit/cdfc006cfb815e0834b18628b7b190056e3a251a))


### Miscellaneous Chores

* **deps:** update apt packages to v1.26.3-3+deb13u6 ([#136](https://github.com/bakerkj/ha-weewx/issues/136)) ([167f726](https://github.com/bakerkj/ha-weewx/commit/167f726805392ea1234d256281a450bd2c4f3932))
* **deps:** update dependency renovate to v43.217.1 ([#137](https://github.com/bakerkj/ha-weewx/issues/137)) ([c0b856e](https://github.com/bakerkj/ha-weewx/commit/c0b856ef248b5fa1c4868999f9f82d65b5dd1e1b))
* **deps:** update dependency renovate to v43.220.0 ([#140](https://github.com/bakerkj/ha-weewx/issues/140)) ([30bdb26](https://github.com/bakerkj/ha-weewx/commit/30bdb26f2acd3604fa2bbb6f4645a3426b0c78fb))
* **deps:** update uv tool to v0.11.20 ([#139](https://github.com/bakerkj/ha-weewx/issues/139)) ([0ca7b0c](https://github.com/bakerkj/ha-weewx/commit/0ca7b0c1755682f6b4e5292c97521bac9878f97c))
* **pre-commit:** migrate prettier mirror to rbubley fork ([#138](https://github.com/bakerkj/ha-weewx/issues/138)) ([e56fd02](https://github.com/bakerkj/ha-weewx/commit/e56fd0239ab687531df76d5ee24282249df82e4f))
* **renovate:** switch apt-package tracking from deb to repology ([#135](https://github.com/bakerkj/ha-weewx/issues/135)) ([784954b](https://github.com/bakerkj/ha-weewx/commit/784954b9f7f6f66628346065c52cd51edb13f319))
* **review:** instruct review bot to use GitHub suggestion blocks ([#142](https://github.com/bakerkj/ha-weewx/issues/142)) ([ffe9686](https://github.com/bakerkj/ha-weewx/commit/ffe96861396a0f43698e3500951d5fb0381d3b4e))


### Tests

* **watchdog:** assert addon stays up on healthy probe ([#131](https://github.com/bakerkj/ha-weewx/issues/131)) ([131e228](https://github.com/bakerkj/ha-weewx/commit/131e228728962be33b2b8a452a082cadbe366c7d))


### Continuous Integration

* **claude:** add missing-tests priority to the review prompt ([#133](https://github.com/bakerkj/ha-weewx/issues/133)) ([39a62de](https://github.com/bakerkj/ha-weewx/commit/39a62de76d47972da8da420f8431253622a6a12d))

## [0.1.14](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.13...ha-weewx-v0.1.14) (2026-06-07)


### Bug Fixes

* **watchdog:** drop X-Ha-Weewx-Addon fingerprint check ([#130](https://github.com/bakerkj/ha-weewx/issues/130)) ([6a209a0](https://github.com/bakerkj/ha-weewx/commit/6a209a0ac7151354e8f7e753e39b49d9445f18f6))


### Miscellaneous Chores

* **deps:** update dependency renovate to v43.214.1 ([#122](https://github.com/bakerkj/ha-weewx/issues/122)) ([75592ef](https://github.com/bakerkj/ha-weewx/commit/75592eff3a9aa0bb7ff91229806c015aee9ff554))
* pin uv to ==0.11.19 and group with Dockerfile uv pin ([#129](https://github.com/bakerkj/ha-weewx/issues/129)) ([7fb4a8c](https://github.com/bakerkj/ha-weewx/commit/7fb4a8c2f02f5cd881860d05f797fce65d43e0ac))


### Continuous Integration

* add Claude Code GitHub workflows ([#120](https://github.com/bakerkj/ha-weewx/issues/120)) ([7efe49d](https://github.com/bakerkj/ha-weewx/commit/7efe49d5346163721267bab8a9ea520476187cb1))
* **claude:** replace plugin path with hand-rolled prompt + built-in MCP ([#127](https://github.com/bakerkj/ha-weewx/issues/127)) ([0e1eb67](https://github.com/bakerkj/ha-weewx/commit/0e1eb6773a443b7224ed304e87f8ce9df5a29a36))
* **claude:** skip release-please PRs and upload Claude JSONL as artifact ([#124](https://github.com/bakerkj/ha-weewx/issues/124)) ([0caf01f](https://github.com/bakerkj/ha-weewx/commit/0caf01fab051cece00fc2a739b045ca9fb2eb142))
* **claude:** skip Renovate/Dependabot PRs from auto code-review ([#123](https://github.com/bakerkj/ha-weewx/issues/123)) ([8588b96](https://github.com/bakerkj/ha-weewx/commit/8588b96fdb1d77f2d0bc1e416a52754c3bce23fb))
* **claude:** strip review prompt to repo description + four categories ([#128](https://github.com/bakerkj/ha-weewx/issues/128)) ([9f8de27](https://github.com/bakerkj/ha-weewx/commit/9f8de274dcad12df1e3a975441ed1fa9c23b5792))
* **renovate:** track two version pins the dashboard was missing ([#125](https://github.com/bakerkj/ha-weewx/issues/125)) ([c1e751e](https://github.com/bakerkj/ha-weewx/commit/c1e751e8a581aed9ee954839dc4502afd59a5f69))

## [0.1.13](https://github.com/bakerkj/ha-weewx/compare/ha-weewx-v0.1.12...ha-weewx-v0.1.13) (2026-06-05)


### Bug Fixes

* **log_to_file:** widen exception net in process_record ([#112](https://github.com/bakerkj/ha-weewx/issues/112)) ([76ce22e](https://github.com/bakerkj/ha-weewx/commit/76ce22e6031644fc5672d445de7be34d5871d5d2))
* **nginx:** harden cache layer (NOAA TZ bug, override denylist, docs) ([#116](https://github.com/bakerkj/ha-weewx/issues/116)) ([15a060b](https://github.com/bakerkj/ha-weewx/commit/15a060bfea9d5c4d6e2c3ec4084f1a887e088416))
* **watchdog:** fingerprint nginx, escalate to SIGKILL, correct docstring ([#115](https://github.com/bakerkj/ha-weewx/issues/115)) ([a633229](https://github.com/bakerkj/ha-weewx/commit/a633229abb85201d89997ec9663b36851b449cdd))


### Miscellaneous Chores

* **build:** tighten plumbing — comments, guards, AST asserts ([#117](https://github.com/bakerkj/ha-weewx/issues/117)) ([5ab5216](https://github.com/bakerkj/ha-weewx/commit/5ab5216d2a05aead55b15cae7be84f413ff3fd45))
* **deps:** update dependency renovate to v43.214.0 ([#118](https://github.com/bakerkj/ha-weewx/issues/118)) ([c333205](https://github.com/bakerkj/ha-weewx/commit/c33320525b790954f7e89aeb5c9aa42f1b534055))


### Code Refactoring

* consolidate e2e test infra under e2e-tests/ ([#119](https://github.com/bakerkj/ha-weewx/issues/119)) ([e8be2ef](https://github.com/bakerkj/ha-weewx/commit/e8be2ef899fa016dd4a5388661ddbf1f67325633))


### Continuous Integration

* tighten e2e timing and avoid gha cache scope contention ([#114](https://github.com/bakerkj/ha-weewx/issues/114)) ([a3260bf](https://github.com/bakerkj/ha-weewx/commit/a3260bf204aafecc5ae23b9105b45fd56a36c74f))

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
