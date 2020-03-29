dev:
	pipenv install --dev

pipenv:
	pip install pipenv
	pipenv install --dev

deploy-patch: clean requirements bumpversion-patch upload clean

deploy-minor: clean requirements bumpversion-minor upload clean

deploy-major: clean requirements bumpversion-major upload clean

requirements:
	pipenv_to_requirements

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
