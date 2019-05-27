RAWVERSION = $(filter-out __version__ = , $(shell grep __version__ multitenancy/__init__.py))
VERSION = $(strip $(shell echo $(RAWVERSION)))
PACKAGE = django-site-multitenancy

.PHONY: clean version 

#======================================================================

clean:
	rm -rf *.tar.gz dist *.egg-info *.rpm *.xml pylint.out
	find . -name "*.pyc" -exec rm '{}' ';'

version:
	@echo ${VERSION}

ctags:
	# This sets up the ./tags file for vim that includes all packages in the virtualenv
	# plus our own code
	ctags -R --fields=+l --languages=python --python-kinds=-iv -f ./tags ./ `python -c "import os, sys; print(' '.join('{}'.format(d) for d in sys.path if os.path.isdir(d)))"`

