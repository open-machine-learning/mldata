VER=r$(shell svn info  | grep Revision | cut -f 2 -d ' ')
RELEASENAME:=mldata-$(VER)
RELEASETAR:=mldata-$(VER).tar.gz
RELEASEDIR:=/tmp/

WEBSITEDIR:=django

HOST=mldata.org

#TODO
#get-live-db:
#	rm -f mldata/mldata.db
#	scp admintools/mysql_to_sqlite.sh mldata@data.ml.tu-berlin.de:
#	cd mldata ; python manage.py syncdb --noinput
#	( ssh mldata@data.ml.tu-berlin.de chmod 700 mysql_to_sqlite.sh \; ./mysql_to_sqlite.sh ) | sqlite3 mldata/mldata.db
#	ssh mldata@data.ml.tu-berlin.de rm -f mysql_to_sqlite.sh


#TODO
#live-backup:
#	ssh mldata@data.ml.tu-berlin.de mysqldump mldata >`date '+%Y-%m-%d'`_mysql.dump

release: clean
#	svn commit
	svn update
	rm -rf $(RELEASEDIR)/$(RELEASENAME)
	svn export . $(RELEASEDIR)/$(RELEASENAME)
	rm -f $(RELEASEDIR)/$(RELEASENAME)/mldata.db $(RELEASEDIR)/$(RELEASENAME)/Makefile
	ssh mldata@$(HOST) rm -rf $(WEBSITEDIR)/$(RELEASENAME) 
	tar cjvf - -C $(RELEASEDIR) $(RELEASENAME) | \
		ssh mldata@$(HOST) \
		\( tar xjvf - -C $(WEBSITEDIR) \; sync \; sync \; sync \; \
		sed -i "s#XXXXXXXXX#\`cat /home/mldata/.mysql_password\`#" $(WEBSITEDIR)/$(RELEASENAME)/settings.py \; \
		sed -i "s#RECAPTCHAPUBLIC#\`cat /home/mldata/.recaptcha_public\`#" $(WEBSITEDIR)/$(RELEASENAME)/settings.py \; \
		sed -i "s#RECAPTCHAPRIVATE#\`cat /home/mldata/.recaptcha_private\`#" $(WEBSITEDIR)/$(RELEASENAME)/settings.py \; \
		sed -i '"s/^PRODUCTION = False/PRODUCTION = True/g"' $(WEBSITEDIR)/$(RELEASENAME)/settings.py \; \
		sed -i '"s/^VERSION = \"r0000\"/VERSION = \"$(VER)\"/g"' $(WEBSITEDIR)/$(RELEASENAME)/settings.py \; \
		python -mcompileall $(WEBSITEDIR)/$(RELEASENAME)/ \; \
		find $(WEBSITEDIR)/$(RELEASENAME) -type d -exec chmod 755 {} '\;' \; \
		find $(WEBSITEDIR)/$(RELEASENAME) -type f -exec chmod 644 {} '\;' \; \
		chmod 640 $(WEBSITEDIR)/$(RELEASENAME)/settings.py\* \; \
		rm -rf static/media \; \
		mv -f $(WEBSITEDIR)/$(RELEASENAME)/media static/ \; \
		cd $(WEBSITEDIR) \; ln -snf $(RELEASENAME) mldata \; \
		sudo /etc/init.d/fapws3 restart \
		\)
	rm -rf $(RELEASEDIR)/$(RELEASENAME)

dev:
	$(MAKE) release HOST=mldata-dev.ml.tu-berlin.de

tar: clean
	rm -rf "$(RELEASEDIR)/$(RELEASENAME)"
	svn export . $(RELEASEDIR)/$(RELEASENAME)
	cd $(RELEASEDIR) && tar czvf $(RELEASETAR) $(RELEASENAME)
	rm -rf "$(RELEASEDIR)/$(RELEASENAME)"

clean:
	find ./ -name '*.pyc' -delete
	find ./ -name '*.swp' -delete

doc:
	DJANGO_SETTINGS_MODULE=settings epydoc --name "API doc for $(HOST)" --url http://$(HOST) --graph=all --html --output doc/ .

checkdoc:
	DJANGO_SETTINGS_MODULE=settings epydoc --check .

.PHONY: doc
