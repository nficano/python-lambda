dev:
	pipenv install --dev

pipenv:
	pip install pipenv
	pipenv install --dev

deploy-patch: requirements bumpversion-patch sdist bdist wheels upload clean

deploy-minor: requirements bumpversion-minor sdist bdist wheels upload clean

deploy-major: requirements bumpversion-major sdist bdist wheels upload clean

requirements:
	pipenv_to_requirements

sdist: requirements
	python setup.py sdist

bdist: requirements
	python setup.py bdist

wheels: requirements
	python setup.py bdist_wheel

bumpversion-patch:
	bumpversion patch
	git push
	git push --tags

bumpversion-minor:
	bumpversion minor
	git push
	git push --tags

bumpversion-major:
	bumpversion major
	git push
	git push --tags

clean: clean-build clean-pyc

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.DS_Store' -exec rm -f {} +
	rm -f requirements.*

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '.pytest_cache' -exec rm -fr {} +
	find . -name '.mypy_cache' -exec rm -fr {} +

upload:
	python setup.py sdist bdist_wheel
	twine upload dist/*
