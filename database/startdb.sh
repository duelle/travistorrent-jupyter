docker run --rm -ti  -p3306:3306 --name mariadb-tt -e MYSQL_USER=bob -e MYSQL_PASSWORD=bobbob -e MYSQL_ROOT_PASSWORD=mdbpass -v $(pwd)/varlibmysql:/var/lib/mysql mariadb
