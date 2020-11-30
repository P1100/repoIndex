# LAS refactoring
A brand new experience with the Lab Assistant Suite

## Requirements
* Docker v.17.12.0-ce or newer
* docker-compose v.1.18.0 or newer

* Django 2.2.17 (six support ended after 3.x)
* Djongo: https://github.com/lasircc/djongo.git

## System architecture

Everything has changed...

-------------------------------

## PyCharm Project setup
```
python -m env repoenv
pip install -r ./las/_config/packaging/requirements.txt
```

## RepoIndex Instructions

` docker cp ./MyRepoindex/genomic_metadata.schema.json a16:/data/web`

