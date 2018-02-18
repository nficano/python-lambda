help:
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "lint - check style with flake8"
	@echo "release - package and upload a release"
	@echo "install - install the package to the active Python's site-packages"

clean: clean-build clean-pyc clean-merge

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-merge:
	find . -name '*.orig' -exec rm -f {} +

lint:
	flake8 python-lambda tests

release: clean
	python setup.py sdist upload
	python setup.py bdist_wheel upload

install: clean
	python setup.py install

test:
	 py.test tests/ --cov aws_lambda --cov-report term-missing

