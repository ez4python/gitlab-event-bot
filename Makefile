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
	git push origin main && git push gitlab main

run:
	docker start tg_redis

check-keys:
	 docker exec -it tg_redis redis-cli keys '*'
