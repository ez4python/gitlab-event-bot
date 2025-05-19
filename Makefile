.PHONY: clean-migrations

PM=python3 manage.py

migrate:
	$(PM) makemigrations
	$(PM) migrate

admin:
	$(PM) createsuperuser

clean-migrations:
	find apps/ -path "*/migrations/*.py" ! -name "__init__.py" -delete
	rm -rf db.sqlite3

push:
	git push github main && git push gitlab main

containers:
	docker start postgres_db redis_db

check-keys:
	 docker exec -it redis_db redis-cli keys '*'
