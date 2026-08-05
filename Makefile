.PHONY: check check-applet install-local uninstall-local dist clean
PYTHON ?= python3
UUID := wirtelprimfgenerator@H234598
DIST := dist

check:
	$(PYTHON) -m json.tool files/$(UUID)/metadata.json >/dev/null
	$(PYTHON) -m json.tool files/$(UUID)/settings-schema.json >/dev/null
	$(PYTHON) -m json.tool config/web-media-limits.json >/dev/null
	$(PYTHON) -m json.tool config/cloudflare-aliases.json >/dev/null
	$(PYTHON) -m py_compile Sourcecode/wirtelprimpf_generator.py
	$(PYTHON) -m py_compile files/$(UUID)/helper.py files/$(UUID)/SettingsLogo.py files/$(UUID)/settings_sync.py
	$(PYTHON) -m py_compile files/$(UUID)/story_directives_core.py files/$(UUID)/StoryDirectives.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/story_blueprint.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_aliases.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_snapshot.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_preflight.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_rollback.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_audit.py
	$(PYTHON) -m py_compile scripts/build_web_status.py
	$(PYTHON) -m py_compile scripts/build_web_site.py scripts/validate_web_plan.py scripts/validate_web_governance.py scripts/validate_web_relations.py scripts/web_inventory.py scripts/web_ids.py scripts/web_content_model.py scripts/web_content_errors.py scripts/validate_web_manifest.py scripts/measure_web_media.py scripts/measure_media_cache_replay.py
	node --check files/$(UUID)/applet.js
	node tests/test_applet_runtime.js
	node --test tests/test_admin_ui.mjs
	$(PYTHON) -m unittest tests.test_semver
	$(PYTHON) -m unittest tests.test_git_object_fallback
	$(PYTHON) -m unittest tests.test_release_publication
	$(PYTHON) -m unittest tests.test_helper_env
	$(PYTHON) -m unittest tests.test_applet_settings_sync
	$(PYTHON) -m unittest tests.test_settings_schema
	$(PYTHON) -m unittest tests.test_story_directives
	$(PYTHON) -m unittest tests.test_flex_contract
	$(PYTHON) -m unittest tests.test_story_blueprint
	$(PYTHON) tests/test_epub_contract.py
	$(PYTHON) tests/test_pages_artifact.py
	$(PYTHON) tests/test_web_build.py
	$(PYTHON) tests/test_check_equivalence.py
	$(PYTHON) -m unittest tests.test_cloudflare_aliases
	$(PYTHON) -m unittest tests.test_cloudflare_snapshot
	$(PYTHON) -m unittest tests.test_cloudflare_preflight
	$(PYTHON) -m unittest tests.test_cloudflare_rollback
	$(PYTHON) -m unittest tests.test_cloudflare_audit
	$(PYTHON) -m unittest tests.platform.test_cloudflare_credentials
	$(PYTHON) -m unittest tests.test_rollout_plan_contract
	$(PYTHON) -m unittest tests.test_web_plan
	$(PYTHON) -m unittest tests.test_web_status tests.test_recovery_contract tests.test_web_publish_policy tests.test_search_source tests.test_optional_scope
	$(PYTHON) -m unittest tests.test_web_inventory
	$(PYTHON) -m unittest tests.test_web_content_schemas
	$(PYTHON) -m unittest tests.test_web_ids
	$(PYTHON) -m unittest tests.test_web_pairing
	$(PYTHON) -m unittest tests.test_web_content_errors
	$(PYTHON) -m unittest tests.test_web_manifest
	$(PYTHON) -m unittest tests.test_web_media_measurement
	$(PYTHON) -m unittest tests.test_media_cache_replay
	$(PYTHON) -m unittest tests.test_web_relations
	$(PYTHON) -m unittest tests.test_web_workflows
	$(PYTHON) tests/test_web_governance.py
	$(PYTHON) scripts/validate_web_plan.py --root .
	$(PYTHON) scripts/validate_web_governance.py --root .
	@test -f files/$(UUID)/assets/settings-header-logo.png
	@test -f files/$(UUID)/assets/settings-footer-logo.png
	@test -f files/$(UUID)/assets/settings-generator-atelier.png
	@test -f files/$(UUID)/assets/settings-generator-machine.png
	@test -f files/$(UUID)/assets/settings-about-story.png
	@test -f files/$(UUID)/assets/settings-about-book.png
	@test -f files/$(UUID)/assets/panel-icon.png
	@test -f files/$(UUID)/assets/panel-icon-moon.png
	@test -f files/$(UUID)/assets/panel-icon-spark.png

check-applet:
	$(PYTHON) -m json.tool files/$(UUID)/metadata.json >/dev/null
	$(PYTHON) -m json.tool files/$(UUID)/settings-schema.json >/dev/null
	$(PYTHON) -m json.tool config/web-media-limits.json >/dev/null
	$(PYTHON) -m json.tool config/cloudflare-aliases.json >/dev/null
	$(PYTHON) -m py_compile Sourcecode/wirtelprimpf_generator.py
	$(PYTHON) -m py_compile files/$(UUID)/helper.py files/$(UUID)/SettingsLogo.py files/$(UUID)/settings_sync.py
	$(PYTHON) -m py_compile files/$(UUID)/story_directives_core.py files/$(UUID)/StoryDirectives.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/story_blueprint.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_aliases.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_snapshot.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_preflight.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_rollback.py
	$(PYTHON) -m py_compile wirtelprimpf_platform/cloudflare_audit.py
	$(PYTHON) -m py_compile scripts/build_web_status.py
	$(PYTHON) -m py_compile scripts/build_web_site.py scripts/validate_web_plan.py scripts/validate_web_governance.py scripts/validate_web_relations.py scripts/web_inventory.py scripts/web_ids.py scripts/web_content_model.py scripts/web_content_errors.py scripts/validate_web_manifest.py scripts/measure_web_media.py scripts/measure_media_cache_replay.py
	node --check files/$(UUID)/applet.js
	node tests/test_applet_runtime.js
	node --test tests/test_admin_ui.mjs
	$(PYTHON) -m unittest tests.test_semver
	$(PYTHON) -m unittest tests.test_git_object_fallback
	$(PYTHON) -m unittest tests.test_release_publication
	$(PYTHON) -m unittest tests.test_helper_env
	$(PYTHON) -m unittest tests.test_applet_settings_sync
	$(PYTHON) -m unittest tests.test_settings_schema
	$(PYTHON) -m unittest tests.test_story_directives
	$(PYTHON) -m unittest tests.test_flex_contract
	$(PYTHON) -m unittest tests.test_story_blueprint
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
