.PHONY: all pep8 pyflakes clean dev

PYTHON=python
GITIGNORES=$(shell cat .gitignore |tr "\\n" ",")

all: pep8

pep8: .gitignore
	env/bin/pep8 . --exclude=$(GITIGNORES)

pyflakes:
	env/bin/pyflakes bootstrap tests

yapf:
	find blueox -name "*.py" | xargs env/bin/yapf -i --style=google
	find bin | xargs env/bin/yapf -i --style=google

dev: env/bin/activate env/.pip

env/bin/activate:
	virtualenv -p $(PYTHON) --no-site-packages env
	echo `pwd`/vendor > env/lib/python2.7/site-packages/vendor.pth

env/.pip: env/bin/activate requirements.txt
	env/bin/pip install -r requirements.txt
	env/bin/pip install -e .
	touch env/.pip

test: env/.pip
	env/bin/testify tests

devclean:
	@rm -rf env

clean:
	@rm -rf build dist
