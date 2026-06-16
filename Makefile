.PHONY: check install-local uninstall-local dist clean
PYTHON ?= python3
UUID := wirtelprimfgenerator@H234598
DIST := dist

check:
	$(PYTHON) -m json.tool files/$(UUID)/metadata.json >/dev/null
	$(PYTHON) -m json.tool files/$(UUID)/settings-schema.json >/dev/null
	$(PYTHON) -m py_compile files/$(UUID)/helper.py files/$(UUID)/SettingsLogo.py
	@test -f files/$(UUID)/assets/settings-header-logo.png
	@test -f files/$(UUID)/assets/settings-footer-logo.png
	@test -f files/$(UUID)/assets/panel-icon.png

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
