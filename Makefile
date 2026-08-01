.PHONY: check install-local uninstall-local dist clean
PYTHON ?= python3
UUID := wirtelprimfgenerator@H234598
DIST := dist

check:
	$(PYTHON) -m json.tool files/$(UUID)/metadata.json >/dev/null
	$(PYTHON) -m json.tool files/$(UUID)/settings-schema.json >/dev/null
	$(PYTHON) -m py_compile Sourcecode/wirtelprimpf_generator.py
	$(PYTHON) -m py_compile files/$(UUID)/helper.py files/$(UUID)/SettingsLogo.py
	$(PYTHON) -m py_compile files/$(UUID)/story_directives_core.py files/$(UUID)/StoryDirectives.py
	node --check files/$(UUID)/applet.js
	node tests/test_applet_runtime.js
	node --test tests/test_admin_ui.mjs
	$(PYTHON) -m unittest tests.test_semver
	$(PYTHON) -m unittest tests.test_git_object_fallback
	$(PYTHON) -m unittest tests.test_release_publication
	$(PYTHON) -m unittest tests.test_helper_env
	$(PYTHON) -m unittest tests.test_settings_schema
	$(PYTHON) -m unittest tests.test_story_directives
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
