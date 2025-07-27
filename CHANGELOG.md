# Changelog

## [5.0.0](https://github.com/stkr22/tts-batch-api-py/compare/v4.1.0...v5.0.0) (2025-07-27)


### ⚠ BREAKING CHANGES

* Switched from StreamingResponse to Response.

### Features

* :sparkles: implement caching for responses  with redis ([2a9e118](https://github.com/stkr22/tts-batch-api-py/commit/2a9e118f1e2e0ce4f8a85f8fa6992da6f1f705b1))
* :sparkles: implement caching for responses  with redis ([bcf353a](https://github.com/stkr22/tts-batch-api-py/commit/bcf353a1d842400b569daba1d5d628fcee242c67)), closes [#2](https://github.com/stkr22/tts-batch-api-py/issues/2)
* ✨ add sample rate conversion and model optimization ([e2ac7a4](https://github.com/stkr22/tts-batch-api-py/commit/e2ac7a46670b7efd603f70b98484c592ff72978f)), closes [#36](https://github.com/stkr22/tts-batch-api-py/issues/36)
* adding en_US ryan model ([9eff5d0](https://github.com/stkr22/tts-batch-api-py/commit/9eff5d040530b41ad4139e7137e6e76949f12b6e))
* update piper-tts to v1.3.0 and fix linting issues [AI] ([8222a08](https://github.com/stkr22/tts-batch-api-py/commit/8222a086a81f1cdad75581e12beceb316b072d9c))


### Bug Fixes

* :bug: Fix issue that existing assets are not recognized ([d45a53b](https://github.com/stkr22/tts-batch-api-py/commit/d45a53bdf07483857b78193938317a889d4cbd53))
* :bug: Fix issue that existing assets are not recognized ([30334e6](https://github.com/stkr22/tts-batch-api-py/commit/30334e699942170b1094697d4b6e25b6207e8976)), closes [#3](https://github.com/stkr22/tts-batch-api-py/issues/3)
* :bug: Fixing broken dependencies ([0d9811f](https://github.com/stkr22/tts-batch-api-py/commit/0d9811fb0c71556f24afefd3fecb51e4045f271c))
* :rotating_light: Adding ignore on redis retrieval -&gt; alwas bytes ([22dbb8a](https://github.com/stkr22/tts-batch-api-py/commit/22dbb8a910372ff6bb2cf7b49445c889cded720c))
* 🐛 resolve sample rate model resolution causing high-pitched audio ([22f23d0](https://github.com/stkr22/tts-batch-api-py/commit/22f23d0e446880175b5145efe1ad3d5a2f1c4f3a))
* 🐛 resolve sample rate model resolution causing high-pitched audio ([7ce4e91](https://github.com/stkr22/tts-batch-api-py/commit/7ce4e9107e467ca60c6a717834faa4dccb0eec7e))
* 🧪 update test to use correct sample_rate field name ([83b2060](https://github.com/stkr22/tts-batch-api-py/commit/83b2060068d5042d9a014f824bce075820971f32))
* hotfix broken container build github variable ([351775a](https://github.com/stkr22/tts-batch-api-py/commit/351775a6114f78ad68017cd7057bc643de237a75))
* hotfixing cmd container ([5c3d190](https://github.com/stkr22/tts-batch-api-py/commit/5c3d1905246d114dd46f1a56f866440bf2bda4d3))
* resolve container module path issue by copying source code directly [AI] ([ac29d7e](https://github.com/stkr22/tts-batch-api-py/commit/ac29d7ea468427341781c357cbf1ea24227549f0))
* resolve setuptools-scm version detection in container build [AI] ([0248519](https://github.com/stkr22/tts-batch-api-py/commit/02485193db61c66e414e20671f128d0b43402366))


### Documentation

* 📚 comprehensive documentation update and code annotation ([2382e49](https://github.com/stkr22/tts-batch-api-py/commit/2382e4962a717dae44613da30cbaad5b39c7fefb))
* 📚 update API documentation for sample rate conversion ([167e0a2](https://github.com/stkr22/tts-batch-api-py/commit/167e0a20dc39de28ab24ce2dd257d90b3949f0ca))
* 📝 update project structure in AGENTS.md ([3152f01](https://github.com/stkr22/tts-batch-api-py/commit/3152f019e4a6e8f3c79d21429414536503453073))

## [4.1.0](https://github.com/stkr22/tts-batch-api-py/compare/v4.0.1...v4.1.0) (2025-07-27)


### Features

* ✨ add sample rate conversion and model optimization ([e2ac7a4](https://github.com/stkr22/tts-batch-api-py/commit/e2ac7a46670b7efd603f70b98484c592ff72978f)), closes [#36](https://github.com/stkr22/tts-batch-api-py/issues/36)
* adding en_US ryan model ([9eff5d0](https://github.com/stkr22/tts-batch-api-py/commit/9eff5d040530b41ad4139e7137e6e76949f12b6e))
* update piper-tts to v1.3.0 and fix linting issues [AI] ([8222a08](https://github.com/stkr22/tts-batch-api-py/commit/8222a086a81f1cdad75581e12beceb316b072d9c))


### Bug Fixes

* :rotating_light: Adding ignore on redis retrieval -&gt; alwas bytes ([22dbb8a](https://github.com/stkr22/tts-batch-api-py/commit/22dbb8a910372ff6bb2cf7b49445c889cded720c))
* 🐛 resolve sample rate model resolution causing high-pitched audio ([22f23d0](https://github.com/stkr22/tts-batch-api-py/commit/22f23d0e446880175b5145efe1ad3d5a2f1c4f3a))
* 🐛 resolve sample rate model resolution causing high-pitched audio ([7ce4e91](https://github.com/stkr22/tts-batch-api-py/commit/7ce4e9107e467ca60c6a717834faa4dccb0eec7e))
* 🧪 update test to use correct sample_rate field name ([83b2060](https://github.com/stkr22/tts-batch-api-py/commit/83b2060068d5042d9a014f824bce075820971f32))
* hotfix broken container build github variable ([351775a](https://github.com/stkr22/tts-batch-api-py/commit/351775a6114f78ad68017cd7057bc643de237a75))
* hotfixing cmd container ([5c3d190](https://github.com/stkr22/tts-batch-api-py/commit/5c3d1905246d114dd46f1a56f866440bf2bda4d3))
* resolve container module path issue by copying source code directly [AI] ([ac29d7e](https://github.com/stkr22/tts-batch-api-py/commit/ac29d7ea468427341781c357cbf1ea24227549f0))
* resolve setuptools-scm version detection in container build [AI] ([0248519](https://github.com/stkr22/tts-batch-api-py/commit/02485193db61c66e414e20671f128d0b43402366))


### Documentation

* 📚 comprehensive documentation update and code annotation ([2382e49](https://github.com/stkr22/tts-batch-api-py/commit/2382e4962a717dae44613da30cbaad5b39c7fefb))
* 📚 update API documentation for sample rate conversion ([167e0a2](https://github.com/stkr22/tts-batch-api-py/commit/167e0a20dc39de28ab24ce2dd257d90b3949f0ca))
* 📝 update project structure in AGENTS.md ([3152f01](https://github.com/stkr22/tts-batch-api-py/commit/3152f019e4a6e8f3c79d21429414536503453073))

## [4.2.0](https://github.com/stkr22/tts-batch-api-py/compare/v4.1.3...v4.2.0) (2025-07-27)


### Features

* ✨ add sample rate conversion and model optimization ([49ec86f](https://github.com/stkr22/tts-batch-api-py/commit/49ec86f32f951a1bc2c2231920d5c6589816444e)), closes [#36](https://github.com/stkr22/tts-batch-api-py/issues/36)


### Bug Fixes

* 🧪 update test to use correct sample_rate field name ([d1b5be7](https://github.com/stkr22/tts-batch-api-py/commit/d1b5be7f8202eead11f1d5368d1ea4f673e92996))


### Documentation

* 📚 comprehensive documentation update and code annotation ([c5cbe37](https://github.com/stkr22/tts-batch-api-py/commit/c5cbe37f5ff64dec617aa9735e5cedc6894307fe))
* 📚 comprehensive documentation update and code annotation ([2382e49](https://github.com/stkr22/tts-batch-api-py/commit/2382e4962a717dae44613da30cbaad5b39c7fefb))
* 📚 update API documentation for sample rate conversion ([8345cfa](https://github.com/stkr22/tts-batch-api-py/commit/8345cfae7eadf8d238ef5ff60a867b6d22195249))
* 📝 update project structure in AGENTS.md ([1506484](https://github.com/stkr22/tts-batch-api-py/commit/1506484d071696c80b27347d7f64c1821d6e2f52))

## [4.1.3](https://github.com/stkr22/tts-batch-api-py/compare/v4.1.2...v4.1.3) (2025-07-26)


### Bug Fixes

* hotfixing cmd container ([6fa189b](https://github.com/stkr22/tts-batch-api-py/commit/6fa189b000ec9fa4f2b9c81c9439a17a7fda7083))

## [4.1.2](https://github.com/stkr22/tts-batch-api-py/compare/v4.1.1...v4.1.2) (2025-07-26)


### Bug Fixes

* resolve container module path issue by copying source code directly [AI] ([1c03799](https://github.com/stkr22/tts-batch-api-py/commit/1c03799262b3b67679bb658d033b5e927508121d))
* resolve container module path issue by copying source code directly [AI] ([ac29d7e](https://github.com/stkr22/tts-batch-api-py/commit/ac29d7ea468427341781c357cbf1ea24227549f0))
* resolve setuptools-scm version detection in container build [AI] ([0248519](https://github.com/stkr22/tts-batch-api-py/commit/02485193db61c66e414e20671f128d0b43402366))

## [4.1.1](https://github.com/stkr22/tts-batch-api-py/compare/v4.1.0...v4.1.1) (2025-07-26)


### Bug Fixes

* hotfix broken container build github variable ([36b4f17](https://github.com/stkr22/tts-batch-api-py/commit/36b4f17a36c5e51f715836a8dfae48880e822d47))

## [4.1.0](https://github.com/stkr22/tts-batch-api-py/compare/v4.0.1...v4.1.0) (2025-07-26)


### Features

* adding en_US ryan model ([866c20d](https://github.com/stkr22/tts-batch-api-py/commit/866c20da2f4f365be7cc02a2d5e84cbb58c0161c))
* update piper-tts to v1.3.0 and fix linting issues [AI] ([8222a08](https://github.com/stkr22/tts-batch-api-py/commit/8222a086a81f1cdad75581e12beceb316b072d9c))


### Bug Fixes

* :rotating_light: Adding ignore on redis retrieval -&gt; alwas bytes ([22dbb8a](https://github.com/stkr22/tts-batch-api-py/commit/22dbb8a910372ff6bb2cf7b49445c889cded720c))
