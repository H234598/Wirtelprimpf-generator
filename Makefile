.PHONY: check install-local uninstall-local dist clean
PYTHON ?= python3
UUID := wirtelprimfgenerator@H234598
DIST := dist

check:
	$(PYTHON) -m json.tool files/$(UUID)/metadata.json >/dev/null
	$(PYTHON) -m json.tool files/$(UUID)/settings-schema.json >/dev/null
	$(PYTHON) -m py_compile Sourcecode/wirtelprimpf_generator.py
	$(PYTHON) -m py_compile files/$(UUID)/helper.py files/$(UUID)/SettingsLogo.py
	$(PYTHON) tests/test_semver.py
	$(PYTHON) tests/test_helper_env.py
	$(PYTHON) tests/test_settings_schema.py
	@test -f files/$(UUID)/assets/settings-header-logo.png
	@test -f files/$(UUID)/assets/settings-footer-logo.png
	@test -f files/$(UUID)/assets/settings-generator-atelier.png
	@test -f files/$(UUID)/assets/settings-generator-machine.png
	@test -f files/$(UUID)/assets/settings-about-story.png
	@test -f files/$(UUID)/assets/settings-about-book.png
	@test -f files/$(UUID)/assets/panel-icon.png
	@test -f files/$(UUID)/assets/panel-icon-moon.png
	@test -f files/$(UUID)/assets/panel-icon-spark.png

install-local:
	./scripts/install-local.sh

uninstall-local:
	./scripts/uninstall-local.sh

dist: check
	mkdir -p $(DIST)
	./scripts/build-zip.sh

clean:
	rm -rf -- $(DIST)
	find . -type d -name __pycache__ -prune -exec rm -rf -- {} +
