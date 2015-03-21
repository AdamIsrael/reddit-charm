
default:
@echo "One of:"
	@echo "    make testdep"
	@echo "    make lint"
	@echo "    make test"
	@echo

sync:
	@bzr cat \
		lp:charm-helpers/tools/charm_helpers_sync/charm_helpers_sync.py \
		> .charm_helpers_sync.py
	@python .charm_helpers_sync.py -c charm-helpers.yaml
	@rm .charm_helpers_sync.py
